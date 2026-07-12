from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.google_health_client import GOOGLE_HEALTH_SCOPES, GoogleHealthClient, MockGoogleHealthClient
from app.health_aggregation import store_physical_heart_rate_rollups
from app.health_models import (
    HealthConnection,
    HealthHeartRateAggregate,
    HealthMetric,
    HealthOAuthState,
    HealthSleepSession,
)
from app.health_schemas import validate_google_data_point
from app.health_sync import _mark_sleep_overlaps, _upsert_metric, _valid_access_token
from app.models import User
from app.security import decrypt_health_secret, encrypt_health_secret, hash_password


def _configure_mock() -> None:
    settings = get_settings()
    settings.google_health_enabled = True
    settings.google_health_mock_mode = True
    settings.google_health_client_id = "test-client"
    settings.google_health_client_secret = "test-secret"
    settings.google_health_redirect_uri = "http://localhost/api/v1/health/oauth/callback"
    settings.google_health_success_redirect_uri = None
    settings.google_health_token_encryption_key = Fernet.generate_key().decode()
    settings.google_health_min_sync_interval_seconds = 0


def test_oauth_state_pkce_encrypted_tokens_replay_and_deletion(client: TestClient, auth: dict[str, str]):
    _configure_mock()
    started = client.post("/api/v1/health/oauth/start", headers=auth)
    assert started.status_code == 200, started.text
    callback_url = started.json()["authorization_url"]
    params = parse_qs(urlsplit(callback_url).query)
    state = params["state"][0]

    with SessionLocal() as db:
        flow = db.scalar(select(HealthOAuthState))
        assert flow.state_hash != state
        assert flow.pkce_verifier_encrypted.startswith("v1:")
        assert len(decrypt_health_secret(flow.pkce_verifier_encrypted) or "") >= 43
        assert flow.requested_scopes == list(GOOGLE_HEALTH_SCOPES)

    callback = client.get(callback_url)
    assert callback.status_code == 200, callback.text
    assert client.get(callback_url).status_code == 400
    status = client.get("/api/v1/health/status", headers=auth)
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert status.json()["missing_scopes"] == []

    with SessionLocal() as db:
        connection = db.scalar(select(HealthConnection))
        assert "mock-access-token" not in connection.access_token_encrypted
        assert decrypt_health_secret(connection.refresh_token_encrypted) == "mock-refresh-token"

    deleted = client.delete("/api/v1/health/connection", headers=auth)
    assert deleted.status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(HealthConnection)) == 0
        assert db.scalar(select(func.count()).select_from(HealthOAuthState)) == 0


def test_redirect_validation_and_versioned_encryption(client: TestClient, auth: dict[str, str]):
    _configure_mock()
    settings = get_settings()
    settings.google_health_redirect_uri = "http://attacker.example/callback"
    assert client.post("/api/v1/health/oauth/start", headers=auth).status_code == 503
    settings.google_health_redirect_uri = "http://localhost/api/v1/health/oauth/callback"
    encrypted = encrypt_health_secret("secret-token")
    assert encrypted.startswith("v1:")
    assert decrypt_health_secret(encrypted) == "secret-token"
    try:
        decrypt_health_secret("v2:unsupported")
    except ValueError:
        pass
    else:
        raise AssertionError("Eine unbekannte Verschlüsselungsversion wurde akzeptiert.")


def test_expired_oauth_state_is_rejected(client: TestClient, auth: dict[str, str]):
    _configure_mock()
    started = client.post("/api/v1/health/oauth/start", headers=auth).json()
    with SessionLocal() as db:
        flow = db.scalar(select(HealthOAuthState))
        flow.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.get(started["authorization_url"]).status_code == 400


def test_expired_access_token_refreshes_and_rotates_refresh_token(auth: dict[str, str]):
    _configure_mock()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        connection = HealthConnection(
            user_id=user.id,
            health_user_id_hash="refresh-user",
            health_user_id_encrypted=encrypt_health_secret("refresh-user"),
            access_token_encrypted=encrypt_health_secret("expired-access"),
            refresh_token_encrypted=encrypt_health_secret("mock-refresh-token"),
            granted_scopes=list(GOOGLE_HEALTH_SCOPES),
            access_token_expires_at=now - timedelta(minutes=1),
        )
        db.add(connection)
        db.commit()
        refreshed = _valid_access_token(db, connection, MockGoogleHealthClient(get_settings()), now)
        assert refreshed == "mock-access-token-refreshed"
        assert decrypt_health_secret(connection.refresh_token_encrypted) == "mock-refresh-token-rotated"
        assert decrypt_health_secret(connection.access_token_encrypted) == refreshed


def test_client_pagination_retry_without_sleep():
    settings = get_settings()
    settings.google_health_max_retries = 2
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, json={"error": "rate"})
        token = request.url.params.get("pageToken")
        if token is None:
            return httpx.Response(200, json={"dataPoints": [{"first": True}], "nextPageToken": "next"})
        return httpx.Response(200, json={"dataPoints": [{"second": True}], "nextPageToken": ""})

    sleeps: list[float] = []
    google = GoogleHealthClient(
        settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleeper=sleeps.append,
        jitter=lambda: 0.0,
    )
    points = list(
        google.reconcile_data_points(
            "access",
            "daily-resting-heart-rate",
            filter_expression='daily_resting_heart_rate.date >= "2026-01-01"',
        )
    )
    assert points == [{"first": True}, {"second": True}]
    assert sleeps == [0.0]
    assert requests[-1].url.params["pageToken"] == "next"


def test_whitelist_validation_and_heart_rate_idempotency(auth: dict[str, str]):
    payload = {
        "dataPointName": "users/x/dataTypes/daily-resting-heart-rate/dataPoints/y",
        "dailyRestingHeartRate": {
            "date": {"year": 2026, "month": 7, "day": 10},
            "beatsPerMinute": "52",
            "untrustedFutureField": {"raw": "discard-me"},
        },
        "untrustedTopLevel": "discard-me",
    }
    value, source, _ = validate_google_data_point(payload, "daily-resting-heart-rate")
    assert value.beatsPerMinute == 52
    assert "untrustedFutureField" not in value.model_dump()
    assert source is None

    _configure_mock()
    with SessionLocal() as db:
        from app.models import User

        user = db.scalar(select(User))
        connection = HealthConnection(
            user_id=user.id,
            health_user_id_hash="external-user",
            health_user_id_encrypted=encrypt_health_secret("external-user"),
            access_token_encrypted=encrypt_health_secret("access"),
            refresh_token_encrypted=encrypt_health_secret("refresh"),
            granted_scopes=list(GOOGLE_HEALTH_SCOPES),
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(connection)
        db.commit()
        point = {
            "startTime": "2026-07-10T12:00:00Z",
            "endTime": "2026-07-10T12:01:00Z",
            "heartRate": {
                "beatsPerMinuteMin": 50,
                "beatsPerMinuteAvg": 60,
                "beatsPerMinuteMax": 70,
            },
        }
        for _ in range(2):
            stored, rejected = store_physical_heart_rate_rollups(
                db,
                user_id=user.id,
                connection_id=connection.id,
                granularity="minute",
                points=[point],
                timezone_name="Europe/Berlin",
            )
            assert (stored, rejected) == (1, 0)
            db.commit()
        assert db.scalar(select(func.count()).select_from(HealthHeartRateAggregate)) == 1


def test_mock_sync_and_owner_scoped_data(client: TestClient, auth: dict[str, str]):
    _configure_mock()
    started = client.post("/api/v1/health/oauth/start", headers=auth).json()
    assert client.get(started["authorization_url"]).status_code == 200
    synced = client.post("/api/v1/health/sync", headers=auth, json={"lookback_days": 7})
    assert synced.status_code == 200, synced.text
    assert synced.json()["status"] == "succeeded"
    repeated = client.post("/api/v1/health/sync", headers=auth, json={})
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["status"] == "succeeded"
    get_settings().google_health_min_sync_interval_seconds = 30
    limited = client.post("/api/v1/health/sync", headers=auth, json={})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    data = client.get("/api/v1/health/data", headers=auth)
    assert data.status_code == 200
    assert set(data.json()) == {"metrics", "heart_rate", "sleeps", "exercises"}
    overview = client.get("/api/v1/health/overview", headers=auth, params={"day": "2026-07-10"})
    assert overview.status_code == 200, overview.text
    assert set(overview.json()["scores"]) == {"recovery", "energy", "training_load", "resilience"}


def test_health_data_is_isolated_between_users(client: TestClient, auth: dict[str, str]):
    _configure_mock()
    with SessionLocal() as db:
        owner = db.scalar(select(User))
        connection = HealthConnection(
            user_id=owner.id,
            health_user_id_hash="owner-google-user",
            health_user_id_encrypted=encrypt_health_secret("owner-google-user"),
            access_token_encrypted=encrypt_health_secret("owner-access"),
            refresh_token_encrypted=encrypt_health_secret("owner-refresh"),
            granted_scopes=list(GOOGLE_HEALTH_SCOPES),
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        stranger = User(
            email="stranger@example.com",
            display_name="Fremdes Konto",
            password_hash=hash_password("very-secure-password"),
        )
        db.add_all([connection, stranger])
        db.flush()
        _upsert_metric(
            db,
            connection,
            "steps",
            "steps",
            12_345,
            "count",
            date(2026, 7, 12),
        )
        db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "stranger@example.com", "password": "very-secure-password"},
    )
    stranger_auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/v1/health/data", headers=stranger_auth).json()["metrics"] == []
    assert client.get("/api/v1/health/status", headers=stranger_auth).json()["connected"] is False
    assert client.get("/api/v1/health/data", headers=auth).json()["metrics"][0]["value"] == 12_345


def test_overlapping_sleep_and_late_metric_update_are_visible_and_idempotent(auth: dict[str, str]):
    _configure_mock()
    with SessionLocal() as db:
        user = db.scalar(select(User))
        connection = HealthConnection(
            user_id=user.id,
            health_user_id_hash="late-google-user",
            health_user_id_encrypted=encrypt_health_secret("late-google-user"),
            access_token_encrypted=encrypt_health_secret("late-access"),
            refresh_token_encrypted=encrypt_health_secret("late-refresh"),
            granted_scopes=list(GOOGLE_HEALTH_SCOPES),
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(connection)
        db.flush()
        for dedupe, start_hour, end_hour in (("sleep-a", 20, 23), ("sleep-b", 22, 23)):
            db.add(
                HealthSleepSession(
                    connection_id=connection.id,
                    user_id=user.id,
                    dedupe_hash=dedupe,
                    start_at=datetime(2026, 7, 11, start_hour, tzinfo=timezone.utc),
                    end_at=datetime(2026, 7, 12, end_hour - 20, tzinfo=timezone.utc),
                    local_date=date(2026, 7, 12),
                    sleep_type="STAGES",
                )
            )
        db.flush()
        _mark_sleep_overlaps(db, connection)
        _upsert_metric(db, connection, "steps", "steps", 1_000, "count", date(2026, 7, 10))
        _upsert_metric(db, connection, "steps", "steps", 1_250, "count", date(2026, 7, 10))
        db.commit()
        sleeps = db.scalars(select(HealthSleepSession)).all()
        metrics = db.scalars(select(HealthMetric).where(HealthMetric.metric_type == "steps")).all()
        assert all(item.overlaps_other_session for item in sleeps)
        assert len(metrics) == 1
        assert metrics[0].value == 1_250
