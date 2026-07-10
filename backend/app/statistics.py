from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .models import Activity


METRIC_KEYS = (
    "activity_count",
    "distance_m",
    "duration_s",
    "moving_time_s",
    "elevation_gain_m",
    "training_load",
    "avg_speed_mps",
    "avg_hr_bpm",
)


def choose_granularity(date_from: date, date_to: date, requested: str = "auto") -> str:
    if requested in {"day", "week", "month"}:
        return requested
    days = max(1, (date_to - date_from).days + 1)
    if days <= 45:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def _bucket_start(value: date, granularity: str) -> date:
    if granularity == "week":
        return value - timedelta(days=value.weekday())
    if granularity == "month":
        return value.replace(day=1)
    return value


def _next_bucket(value: date, granularity: str) -> date:
    if granularity == "week":
        return value + timedelta(days=7)
    if granularity == "month":
        return (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return value + timedelta(days=1)


def totals(activities: Iterable[Activity]) -> dict[str, Any]:
    items = list(activities)
    distance = sum(activity.distance_m for activity in items)
    duration = sum(activity.duration_s for activity in items)
    moving = sum(activity.moving_time_s for activity in items)
    hr_weight = sum(activity.moving_time_s for activity in items if activity.avg_hr_bpm is not None)
    weighted_hr = sum(
        float(activity.avg_hr_bpm) * activity.moving_time_s
        for activity in items
        if activity.avg_hr_bpm is not None
    )
    return {
        "activity_count": len(items),
        "distance_m": round(distance, 2),
        "duration_s": round(duration, 2),
        "moving_time_s": round(moving, 2),
        "elevation_gain_m": round(sum(activity.elevation_gain_m for activity in items), 2),
        "training_load": round(sum(activity.training_load for activity in items), 2),
        "avg_speed_mps": round(distance / moving, 3) if moving else None,
        "avg_hr_bpm": round(weighted_hr / hr_weight, 1) if hr_weight else None,
    }


def _series(
    activities: list[Activity],
    date_from: date,
    date_to: date,
    granularity: str,
    timezone_name: str,
) -> list[dict[str, Any]]:
    local_timezone = ZoneInfo(timezone_name)
    grouped: dict[date, list[Activity]] = defaultdict(list)
    for activity in activities:
        started_at = activity.started_at if activity.started_at.tzinfo else activity.started_at.replace(tzinfo=ZoneInfo("UTC"))
        grouped[_bucket_start(started_at.astimezone(local_timezone).date(), granularity)].append(activity)
    current = _bucket_start(date_from, granularity)
    end = _bucket_start(date_to, granularity)
    result: list[dict[str, Any]] = []
    bucket_count = 0
    while current <= end and bucket_count < 5_000:
        result.append({"period_start": current.isoformat(), **totals(grouped.get(current, []))})
        current = _next_bucket(current, granularity)
        bucket_count += 1
    return result


def _percent_change(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None or float(previous) == 0:
        return None
    return round((float(current) - float(previous)) / abs(float(previous)) * 100, 1)


def build_statistics(
    activities: list[Activity],
    previous_activities: list[Activity],
    date_from: date,
    date_to: date,
    previous_from: date,
    previous_to: date,
    requested_granularity: str = "auto",
    timezone_name: str = "UTC",
) -> dict[str, Any]:
    granularity = choose_granularity(date_from, date_to, requested_granularity)
    current_totals = totals(activities)
    previous_totals = totals(previous_activities)
    changes = {
        key: _percent_change(current_totals.get(key), previous_totals.get(key))
        for key in METRIC_KEYS
    }
    monthly: dict[str, list[Activity]] = defaultdict(list)
    local_timezone = ZoneInfo(timezone_name)
    for activity in activities:
        started_at = activity.started_at if activity.started_at.tzinfo else activity.started_at.replace(tzinfo=ZoneInfo("UTC"))
        monthly[started_at.astimezone(local_timezone).strftime("%Y-%m")].append(activity)
    by_month = [
        {"month": month, **totals(values)}
        for month, values in sorted(monthly.items())
    ]
    return {
        **current_totals,
        "granularity": granularity,
        "series": _series(activities, date_from, date_to, granularity, timezone_name),
        "comparison": {
            "date_from": previous_from.isoformat(),
            "date_to": previous_to.isoformat(),
            **previous_totals,
            "changes": changes,
        },
        "by_month": by_month,
    }
