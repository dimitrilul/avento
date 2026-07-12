from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import Settings, get_settings


GOOGLE_HEALTH_SCOPES = (
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GoogleHealthError(Exception):
    def __init__(self, code: str, *, status_code: int = 502, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class GoogleHealthClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings or get_settings()
        self._client = client or httpx.Client(
            timeout=self.settings.google_health_timeout_seconds,
            follow_redirects=False,
        )
        self._sleeper = sleeper
        self._jitter = jitter

    def authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        self._require_oauth_configuration()
        params = {
            "client_id": self.settings.google_health_client_id or "",
            "redirect_uri": self.settings.google_health_redirect_uri or "",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "scope": " ".join(GOOGLE_HEALTH_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.settings.google_health_authorization_url}?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        self._require_oauth_configuration()
        return self._token_request(
            {
                "code": code,
                "client_id": self.settings.google_health_client_id,
                "client_secret": self.settings.google_health_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            }
        )

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        self._require_oauth_configuration()
        return self._token_request(
            {
                "client_id": self.settings.google_health_client_id,
                "client_secret": self.settings.google_health_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        )

    def revoke_token(self, token: str) -> bool:
        if not token:
            return False
        try:
            response = self._client.post(
                self.settings.google_health_revoke_url,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError:
            return False
        return response.status_code in {200, 204}

    def get_identity(self, access_token: str) -> dict[str, str]:
        data = self._request_json("GET", f"{self.settings.google_health_api_base_url}/users/me/identity", access_token)
        health_user_id = data.get("healthUserId")
        if not isinstance(health_user_id, str) or not 1 <= len(health_user_id) <= 63:
            raise GoogleHealthError("invalid_identity_response")
        # legacyUserId is deliberately not retained for a new v4 integration.
        return {"health_user_id": health_user_id}

    def list_data_points(
        self,
        access_token: str,
        data_type: str,
        *,
        filter_expression: str,
        page_size: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        page_size = page_size or (25 if data_type in {"sleep", "exercise"} else 1440)
        url = f"{self.settings.google_health_api_base_url}/users/me/dataTypes/{data_type}/dataPoints"
        yield from self._paginate_get(
            url,
            access_token,
            item_field="dataPoints",
            params={"filter": filter_expression, "pageSize": min(page_size, 10000)},
        )

    def reconcile_data_points(
        self,
        access_token: str,
        data_type: str,
        *,
        filter_expression: str,
        page_size: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        page_size = page_size or (25 if data_type in {"sleep", "exercise"} else 1440)
        url = f"{self.settings.google_health_api_base_url}/users/me/dataTypes/{data_type}/dataPoints:reconcile"
        yield from self._paginate_get(
            url,
            access_token,
            item_field="dataPoints",
            params={
                "filter": filter_expression,
                "pageSize": min(page_size, 10000),
                "dataSourceFamily": "users/me/dataSourceFamilies/all-sources",
            },
        )

    def rollup_data_points(
        self,
        access_token: str,
        data_type: str,
        *,
        start: datetime,
        end: datetime,
        window_seconds: int,
    ) -> Iterator[dict[str, Any]]:
        if start.tzinfo is None or end.tzinfo is None or end <= start or window_seconds < 1:
            raise ValueError("Ungültiger Rollup-Zeitraum.")
        url = f"{self.settings.google_health_api_base_url}/users/me/dataTypes/{data_type}/dataPoints:rollUp"
        body: dict[str, Any] = {
            "range": {"startTime": _rfc3339(start), "endTime": _rfc3339(end)},
            "windowSize": f"{window_seconds}s",
            "pageSize": 10000,
            "dataSourceFamily": "users/me/dataSourceFamilies/all-sources",
        }
        yield from self._paginate_post(url, access_token, item_field="rollupDataPoints", body=body)

    def daily_rollup_data_points(
        self,
        access_token: str,
        data_type: str,
        *,
        start: date,
        end: date,
    ) -> Iterator[dict[str, Any]]:
        if end <= start:
            raise ValueError("Ungültiger täglicher Rollup-Zeitraum.")
        url = f"{self.settings.google_health_api_base_url}/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp"
        body: dict[str, Any] = {
            "range": {
                "start": {"date": {"year": start.year, "month": start.month, "day": start.day}, "time": {}},
                "end": {"date": {"year": end.year, "month": end.month, "day": end.day}, "time": {}},
            },
            "windowSizeDays": 1,
            "pageSize": 10000,
            "dataSourceFamily": "users/me/dataSourceFamilies/all-sources",
        }
        yield from self._paginate_post(url, access_token, item_field="rollupDataPoints", body=body)

    def _paginate_get(
        self,
        url: str,
        access_token: str,
        *,
        item_field: str,
        params: Mapping[str, Any],
    ) -> Iterator[dict[str, Any]]:
        token: str | None = None
        seen: set[str] = set()
        for _ in range(1000):
            current = dict(params)
            if token:
                current["pageToken"] = token
            payload = self._request_json("GET", url, access_token, params=current)
            yield from _validated_items(payload, item_field)
            token = _next_page_token(payload)
            if not token:
                return
            if token in seen:
                raise GoogleHealthError("repeated_page_token")
            seen.add(token)
        raise GoogleHealthError("pagination_limit_exceeded")

    def _paginate_post(
        self,
        url: str,
        access_token: str,
        *,
        item_field: str,
        body: Mapping[str, Any],
    ) -> Iterator[dict[str, Any]]:
        token: str | None = None
        seen: set[str] = set()
        for _ in range(1000):
            current = dict(body)
            if token:
                current["pageToken"] = token
            payload = self._request_json("POST", url, access_token, json=current)
            yield from _validated_items(payload, item_field)
            token = _next_page_token(payload)
            if not token:
                return
            if token in seen:
                raise GoogleHealthError("repeated_page_token")
            seen.add(token)
        raise GoogleHealthError("pagination_limit_exceeded")

    def _token_request(self, data: Mapping[str, Any]) -> dict[str, Any]:
        # Authorization codes and refresh responses can be one-time/rotating;
        # ambiguous network failures are therefore not retried blindly.
        try:
            response = self._client.post(
                self.settings.google_health_token_url,
                data=data,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise GoogleHealthError("token_endpoint_unavailable") from exc
        if response.status_code != 200:
            raise GoogleHealthError("token_exchange_failed", status_code=401)
        payload = _safe_json(response)
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not access_token or not isinstance(expires_in, int):
            raise GoogleHealthError("invalid_token_response")
        scopes = payload.get("scope", "")
        if not isinstance(scopes, str):
            raise GoogleHealthError("invalid_token_response")
        payload["scope"] = scopes.split()
        return payload

    def _request_json(
        self,
        method: str,
        url: str,
        access_token: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        headers.update({"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
        attempts = self.settings.google_health_max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._client.request(method, url, headers=headers, **kwargs)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt + 1 >= attempts:
                    raise GoogleHealthError("api_unavailable", retryable=True) from exc
                self._sleeper(self._delay(attempt, None))
                continue
            if response.status_code in RETRYABLE_STATUS and attempt + 1 < attempts:
                self._sleeper(self._delay(attempt, response.headers.get("Retry-After")))
                continue
            if response.status_code == 401:
                raise GoogleHealthError("invalid_or_expired_google_token", status_code=401)
            if response.status_code == 403:
                raise GoogleHealthError("google_scope_or_account_forbidden", status_code=403)
            if response.status_code >= 400:
                raise GoogleHealthError(
                    "google_health_rate_limited" if response.status_code == 429 else "google_health_api_error",
                    status_code=response.status_code,
                    retryable=response.status_code in RETRYABLE_STATUS,
                )
            return _safe_json(response)
        raise GoogleHealthError("api_unavailable", retryable=True)

    def _delay(self, attempt: int, retry_after: str | None) -> float:
        parsed = _retry_after_seconds(retry_after)
        if parsed is not None:
            return min(60.0, max(0.0, parsed))
        return min(30.0, (2**attempt) + self._jitter())

    def _require_oauth_configuration(self) -> None:
        if not self.settings.google_health_client_id or not self.settings.google_health_client_secret:
            raise GoogleHealthError("google_health_not_configured", status_code=503)
        if not self.settings.google_health_redirect_uri:
            raise GoogleHealthError("google_health_redirect_not_configured", status_code=503)


class MockGoogleHealthClient(GoogleHealthClient):
    """Deterministic local provider; it never contacts Google."""

    def authorization_url(self, *, state: str, code_challenge: str) -> str:
        del code_challenge
        redirect = self.settings.google_health_redirect_uri
        if not redirect:
            raise GoogleHealthError("google_health_redirect_not_configured", status_code=503)
        return f"{redirect}?{urlencode({'code': 'mock-code', 'state': state})}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        if code != "mock-code" or not code_verifier or redirect_uri != self.settings.google_health_redirect_uri:
            raise GoogleHealthError("token_exchange_failed", status_code=401)
        return {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600,
            "refresh_token_expires_in": 604800,
            "scope": list(GOOGLE_HEALTH_SCOPES),
        }

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        if not refresh_token.startswith("mock-refresh-token"):
            raise GoogleHealthError("token_exchange_failed", status_code=401)
        return {
            "access_token": "mock-access-token-refreshed",
            "refresh_token": "mock-refresh-token-rotated",
            "expires_in": 3600,
            "scope": list(GOOGLE_HEALTH_SCOPES),
        }

    def revoke_token(self, token: str) -> bool:
        return bool(token)

    def get_identity(self, access_token: str) -> dict[str, str]:
        if not access_token.startswith("mock-access-token"):
            raise GoogleHealthError("invalid_or_expired_google_token", status_code=401)
        return {"health_user_id": "mock-google-health-user"}

    def list_data_points(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return iter(())

    def reconcile_data_points(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return iter(())

    def rollup_data_points(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return iter(())

    def daily_rollup_data_points(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return iter(())


def get_google_health_client(settings: Settings | None = None) -> GoogleHealthClient:
    resolved = settings or get_settings()
    return MockGoogleHealthClient(resolved) if resolved.google_health_mock_mode else GoogleHealthClient(resolved)


def _validated_items(payload: dict[str, Any], field: str) -> list[dict[str, Any]]:
    raw = payload.get(field, [])
    if not isinstance(raw, list) or len(raw) > 10000:
        raise GoogleHealthError("invalid_page_response")
    if any(not isinstance(item, dict) for item in raw):
        raise GoogleHealthError("invalid_page_response")
    return raw


def _next_page_token(payload: dict[str, Any]) -> str | None:
    token = payload.get("nextPageToken")
    if token in {None, ""}:
        return None
    if not isinstance(token, str) or len(token) > 4096:
        raise GoogleHealthError("invalid_page_response")
    return token


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit() and int(content_length) > 10 * 1024 * 1024:
        raise GoogleHealthError("response_too_large")
    if len(response.content) > 10 * 1024 * 1024:
        raise GoogleHealthError("response_too_large")
    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleHealthError("invalid_json_response") from exc
    if not isinstance(payload, dict):
        raise GoogleHealthError("invalid_json_response")
    return payload


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return (when - datetime.now(timezone.utc)).total_seconds()


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
