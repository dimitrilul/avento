from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy.orm import Session

from .gamification import replace_activity_discoveries
from .geography import (
    ReverseGeocodingConfigurationError,
    ReverseGeocodingRateLimitError,
    ReverseGeocodingTemporaryError,
    reverse_geocode_track,
    reverse_geocoding_configuration_status,
)
from .models import Activity, utcnow


@dataclass(frozen=True)
class GeographyRefreshResult:
    status: str
    place_count: int
    rate_limited: bool = False
    retry_after_seconds: int | None = None


def _cached_places(activity: Activity) -> list[Mapping[str, Any]]:
    for container in (activity.geography_data, activity.weather):
        if not isinstance(container, Mapping):
            continue
        places = container.get("route_places")
        if isinstance(places, list):
            return [item for item in places if isinstance(item, Mapping)]
    return []


def _provider_data(settings: Any) -> dict[str, Any]:
    configuration = reverse_geocoding_configuration_status(settings)
    return {
        "provider": configuration.get("provider") or "disabled",
        "attribution": configuration.get("attribution_label"),
        "attribution_url": configuration.get("attribution_url"),
    }


def _store_places(activity: Activity, settings: Any, places: list[Mapping[str, Any]]) -> None:
    provider_data = _provider_data(settings)
    if places:
        provider_data["provider"] = places[0].get("provider") or provider_data["provider"]
        provider_data["attribution"] = places[0].get("attribution") or provider_data["attribution"]
    activity.geography_data = {**provider_data, "route_places": [dict(item) for item in places]}
    activity.geography_status = "available" if places else "unavailable"
    activity.geography_updated_at = utcnow()


def refresh_activity_geography(
    db: Session,
    activity: Activity,
    settings: Any,
    *,
    force: bool = False,
) -> GeographyRefreshResult:
    """Refresh one activity without allowing provider failures to abort its transaction."""

    cached = _cached_places(activity)
    if cached and not force:
        _store_places(activity, settings, cached)
        replace_activity_discoveries(db, activity.user_id, activity.id, cached)
        return GeographyRefreshResult("available", len(cached))

    configuration = reverse_geocoding_configuration_status(settings)
    if configuration["status"] != "ready":
        if not cached:
            activity.geography_data = _provider_data(settings)
            activity.geography_status = "error" if configuration["status"] == "misconfigured" else "unavailable"
            activity.geography_updated_at = utcnow()
        return GeographyRefreshResult(activity.geography_status, len(cached))

    activity.geography_status = "pending"
    try:
        places = reverse_geocode_track(activity.track_points or [], settings, raise_errors=True)
    except ReverseGeocodingRateLimitError as exc:
        retry_after = exc.retry_after_seconds or 60
        retry_at = utcnow() + timedelta(seconds=retry_after)
        activity.geography_data = {
            **(dict(activity.geography_data) if isinstance(activity.geography_data, Mapping) else _provider_data(settings)),
            "error_code": "rate_limited",
            "retry_at": retry_at.isoformat(),
        }
        activity.geography_status = "error"
        activity.geography_updated_at = utcnow()
        return GeographyRefreshResult("error", len(cached), True, retry_after)
    except ReverseGeocodingConfigurationError:
        activity.geography_data = {
            **(dict(activity.geography_data) if isinstance(activity.geography_data, Mapping) else _provider_data(settings)),
            "error_code": "misconfigured",
        }
        activity.geography_status = "error"
        activity.geography_updated_at = utcnow()
        return GeographyRefreshResult("error", len(cached))
    except ReverseGeocodingTemporaryError:
        activity.geography_data = {
            **(dict(activity.geography_data) if isinstance(activity.geography_data, Mapping) else _provider_data(settings)),
            "error_code": "temporary",
        }
        activity.geography_status = "error"
        activity.geography_updated_at = utcnow()
        return GeographyRefreshResult("error", len(cached))

    _store_places(activity, settings, places)
    replace_activity_discoveries(db, activity.user_id, activity.id, places)
    return GeographyRefreshResult(activity.geography_status, len(places))


def activity_needs_geography_backfill(activity: Activity, provider: str, *, retry_failed: bool = False) -> bool:
    data = activity.geography_data if isinstance(activity.geography_data, Mapping) else {}
    stored_provider = str(data.get("provider") or "").casefold()
    if activity.geography_status == "pending":
        return True
    if activity.geography_status == "unavailable" and stored_provider != provider.casefold():
        return True
    return retry_failed and activity.geography_status == "error"


def geocoding_status_for_activities(settings: Any, activities: Iterable[Activity]) -> dict[str, str | None]:
    status = reverse_geocoding_configuration_status(settings)
    if status["status"] != "ready":
        return status
    now = datetime.now(timezone.utc)
    current_provider = str(status.get("provider") or "").casefold()
    provider_activities = [
        activity
        for activity in activities
        if isinstance(activity.geography_data, Mapping)
        and str(activity.geography_data.get("provider") or "").casefold() == current_provider
        and activity.geography_updated_at is not None
    ]
    if not provider_activities:
        return status
    activity = max(
        provider_activities,
        key=lambda item: item.geography_updated_at.replace(tzinfo=timezone.utc)
        if item.geography_updated_at and item.geography_updated_at.tzinfo is None
        else item.geography_updated_at,
    )
    data = activity.geography_data if isinstance(activity.geography_data, Mapping) else {}
    if activity.geography_status == "error" and data.get("error_code") == "misconfigured":
        return {**status, "status": "misconfigured"}
    if activity.geography_status == "error" and data.get("error_code") == "rate_limited" and data.get("retry_at"):
        try:
            retry_at = datetime.fromisoformat(str(data["retry_at"]))
            retry_at = retry_at if retry_at.tzinfo else retry_at.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return status
        if retry_at > now:
            return {**status, "status": "rate_limited"}
    return status
