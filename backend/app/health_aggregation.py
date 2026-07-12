from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .health_models import HealthHeartRateAggregate
from .health_schemas import GoogleDailyRollupPoint, GooglePhysicalRollupPoint


def stable_hash(*parts: object) -> str:
    serialized = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def store_physical_heart_rate_rollups(
    db: Session,
    *,
    user_id: str,
    connection_id: str,
    granularity: str,
    points: list[dict],
    timezone_name: str,
    sleep_session_id: str | None = None,
    exercise_id: str | None = None,
) -> tuple[int, int]:
    stored = rejected = 0
    zone = ZoneInfo(timezone_name)
    for raw in points:
        try:
            point = GooglePhysicalRollupPoint.model_validate(raw)
            if point.heartRate is None:
                continue
            start = _aware(point.startTime)
            end = _aware(point.endTime)
            if end <= start:
                raise ValueError("Ungültiges Herzfrequenzintervall")
            values = point.heartRate
            dedupe = stable_hash(
                "google-health-v4",
                granularity,
                start.isoformat(),
                end.isoformat(),
                sleep_session_id,
                exercise_id,
            )
            existing = db.scalar(
                select(HealthHeartRateAggregate).where(
                    HealthHeartRateAggregate.connection_id == connection_id,
                    HealthHeartRateAggregate.dedupe_hash == dedupe,
                )
            )
            if existing is None:
                existing = HealthHeartRateAggregate(
                    connection_id=connection_id,
                    user_id=user_id,
                    dedupe_hash=dedupe,
                    granularity=granularity,
                    start_at=start,
                    end_at=end,
                    local_date=start.astimezone(zone).date(),
                    sleep_session_id=sleep_session_id,
                    exercise_id=exercise_id,
                )
                db.add(existing)
            existing.min_bpm = values.beatsPerMinuteMin
            existing.avg_bpm = values.beatsPerMinuteAvg
            existing.max_bpm = values.beatsPerMinuteMax
            existing.imported_at = datetime.now(timezone.utc)
            stored += 1
        except (TypeError, ValueError):
            rejected += 1
    return stored, rejected


def store_daily_heart_rate_rollups(
    db: Session,
    *,
    user_id: str,
    connection_id: str,
    points: list[dict],
    timezone_name: str,
) -> tuple[int, int]:
    stored = rejected = 0
    zone = ZoneInfo(timezone_name)
    for raw in points:
        try:
            point = GoogleDailyRollupPoint.model_validate(raw)
            if point.heartRate is None:
                continue
            local_date = point.civilStartTime.date.as_date()
            start = datetime.combine(local_date, time.min, zone).astimezone(timezone.utc)
            end_date = point.civilEndTime.date.as_date()
            end = datetime.combine(end_date, time.min, zone).astimezone(timezone.utc)
            values = point.heartRate
            dedupe = stable_hash("google-health-v4", "day", local_date.isoformat())
            existing = db.scalar(
                select(HealthHeartRateAggregate).where(
                    HealthHeartRateAggregate.connection_id == connection_id,
                    HealthHeartRateAggregate.dedupe_hash == dedupe,
                )
            )
            if existing is None:
                existing = HealthHeartRateAggregate(
                    connection_id=connection_id,
                    user_id=user_id,
                    dedupe_hash=dedupe,
                    granularity="day",
                    start_at=start,
                    end_at=end,
                    local_date=local_date,
                )
                db.add(existing)
            existing.min_bpm = values.beatsPerMinuteMin
            existing.avg_bpm = values.beatsPerMinuteAvg
            existing.max_bpm = values.beatsPerMinuteMax
            existing.imported_at = datetime.now(timezone.utc)
            stored += 1
        except (TypeError, ValueError):
            rejected += 1
    return stored, rejected


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
