from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from math import isfinite
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .google_health_client import GOOGLE_HEALTH_SCOPES, GoogleHealthClient, GoogleHealthError
from .health_aggregation import (
    stable_hash,
    store_daily_heart_rate_rollups,
    store_physical_heart_rate_rollups,
)
from .health_models import (
    HealthConnection,
    HealthDataGap,
    HealthDataSource,
    HealthExercise,
    HealthHeartRateZone,
    HealthMetric,
    HealthSleepSession,
    HealthSleepStage,
    HealthSyncCursor,
    HealthSyncRun,
)
from .health_schemas import (
    GoogleDailyHeartRateVariability,
    GoogleDailyHeartRateZones,
    GoogleDailyOxygenSaturation,
    GoogleDailyRespiratoryRate,
    GoogleDailyRestingHeartRate,
    GoogleDailyRollupPoint,
    GoogleExercise,
    GoogleRespiratorySleepSummary,
    GoogleSleep,
    validate_google_data_point,
)
from .security import decrypt_health_secret, encrypt_health_secret


DAILY_DATA_TYPES = (
    "daily-resting-heart-rate",
    "daily-heart-rate-variability",
    "daily-respiratory-rate",
    "daily-oxygen-saturation",
    "daily-heart-rate-zones",
)


def synchronize_health_data(
    db: Session,
    *,
    connection: HealthConnection,
    client: GoogleHealthClient,
    lookback_days: int | None = None,
    now: datetime | None = None,
) -> HealthSyncRun:
    settings = get_settings()
    now = now or datetime.now(timezone.utc)
    days = lookback_days or settings.google_health_initial_sync_days
    cursor_dates = [_aware(cursor.completed_through) for cursor in connection.cursors if cursor.completed_through]
    if lookback_days is None and cursor_dates:
        start = min(cursor_dates) - timedelta(days=settings.google_health_overlap_days)
    else:
        start = now - timedelta(days=days)
    start = max(start, now - timedelta(days=365))
    run = HealthSyncRun(
        connection_id=connection.id,
        user_id=connection.user_id,
        range_start=start,
        range_end=now,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        access_token = _valid_access_token(db, connection, client, now)
        for data_type in DAILY_DATA_TYPES:
            _sync_data_type(db, run, connection, client, access_token, data_type, start, now)
        _sync_data_type(db, run, connection, client, access_token, "sleep", start, now, raw_list=True)
        _sync_data_type(db, run, connection, client, access_token, "exercise", start, now, raw_list=True)
        _sync_data_type(
            db, run, connection, client, access_token, "respiratory-rate-sleep-summary", start, now
        )
        _sync_daily_rollups(db, run, connection, client, access_token, start, now)
        _sync_heart_rate(db, run, connection, client, access_token, start, now)
        _mark_sleep_overlaps(db, connection)
        _sync_context_heart_rate(db, run, connection, client, access_token, start, now)
        _refresh_gaps(db, connection, start.date(), now.date())
        connection.status = "connected"
        connection.last_error_code = None
        connection.last_sync_at = now
        run.status = "partial" if run.rejected_count else "succeeded"
    except GoogleHealthError as exc:
        run.status = "failed"
        run.error_code = exc.code
        connection.last_error_code = exc.code
        if exc.status_code in {401, 403}:
            connection.status = "reauthorization_required"
    except Exception:
        # Never persist provider payloads or exception text; the stable code is
        # enough for audit and does not risk leaking tokens/health values.
        run.status = "failed"
        run.error_code = "health_sync_failed"
        connection.last_error_code = run.error_code
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def _valid_access_token(
    db: Session,
    connection: HealthConnection,
    client: GoogleHealthClient,
    now: datetime,
) -> str:
    access = decrypt_health_secret(connection.access_token_encrypted)
    if access and _aware(connection.access_token_expires_at) > now + timedelta(seconds=60):
        return access
    refresh = decrypt_health_secret(connection.refresh_token_encrypted)
    if not refresh:
        raise GoogleHealthError("google_reauthorization_required", status_code=401)
    token = client.refresh_token(refresh)
    scopes = token.get("scope") or connection.granted_scopes
    if not set(GOOGLE_HEALTH_SCOPES).issubset(set(scopes)):
        raise GoogleHealthError("missing_google_health_scopes", status_code=403)
    connection.access_token_encrypted = encrypt_health_secret(token["access_token"])
    if token.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_health_secret(token["refresh_token"])
    connection.access_token_expires_at = now + timedelta(seconds=int(token["expires_in"]))
    connection.granted_scopes = list(scopes)
    db.commit()
    return token["access_token"]


def _sync_data_type(
    db: Session,
    run: HealthSyncRun,
    connection: HealthConnection,
    client: GoogleHealthClient,
    access_token: str,
    data_type: str,
    start: datetime,
    end: datetime,
    *,
    raw_list: bool = False,
) -> None:
    filter_expression = _filter_for(data_type, start, end)
    iterator = (
        client.list_data_points(access_token, data_type, filter_expression=filter_expression)
        if raw_list
        else client.reconcile_data_points(access_token, data_type, filter_expression=filter_expression)
    )
    points = list(iterator)
    run.fetched_count += len(points)
    seen: set[str] = set()
    for point in points:
        try:
            value, source_payload, external_name = validate_google_data_point(point, data_type)
            source_id = _source_id(db, connection.id, source_payload.model_dump() if source_payload else None)
            if isinstance(value, GoogleSleep):
                key = _store_sleep(db, connection, value, external_name, source_id)
                seen.add(key)
            elif isinstance(value, GoogleExercise):
                key = _store_exercise(db, connection, value, external_name, source_id)
                seen.add(key)
            else:
                _store_daily_value(db, connection, data_type, value, source_id)
            run.stored_count += 1
        except (ValidationError, ValueError, TypeError, OverflowError):
            run.rejected_count += 1
    if data_type == "sleep":
        _delete_stale_sessions(db, connection.id, start, end, seen)
    elif data_type == "exercise":
        _delete_stale_exercises(db, connection.id, start, end, seen)
    _advance_cursor(db, connection.id, data_type, end)
    db.commit()


def _store_daily_value(
    db: Session,
    connection: HealthConnection,
    data_type: str,
    value: Any,
    source_id: str | None,
) -> None:
    metrics: list[tuple[str, float, str]] = []
    if isinstance(value, GoogleDailyRestingHeartRate):
        day = value.date.as_date()
        metrics = [("resting_heart_rate", float(value.beatsPerMinute), "bpm")]
    elif isinstance(value, GoogleDailyHeartRateVariability):
        day = value.date.as_date()
        metrics = _optional_metrics(
            ("hrv_rmssd", value.averageHeartRateVariabilityMilliseconds, "ms"),
            ("non_rem_heart_rate", value.nonRemHeartRateBeatsPerMinute, "bpm"),
            ("hrv_entropy", value.entropy, "score"),
            ("deep_sleep_hrv_rmssd", value.deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds, "ms"),
        )
    elif isinstance(value, GoogleDailyRespiratoryRate):
        day = value.date.as_date()
        metrics = [("respiratory_rate", value.breathsPerMinute, "breaths/min")]
    elif isinstance(value, GoogleDailyOxygenSaturation):
        day = value.date.as_date()
        metrics = _optional_metrics(
            ("spo2_average", value.averagePercentage, "%"),
            ("spo2_lower_bound", value.lowerBoundPercentage, "%"),
            ("spo2_upper_bound", value.upperBoundPercentage, "%"),
            ("spo2_standard_deviation", value.standardDeviationPercentage, "%"),
        )
    elif isinstance(value, GoogleDailyHeartRateZones):
        day = value.date.as_date()
        for zone in value.heartRateZones:
            existing = db.scalar(
                select(HealthHeartRateZone).where(
                    HealthHeartRateZone.connection_id == connection.id,
                    HealthHeartRateZone.local_date == day,
                    HealthHeartRateZone.zone_type == zone.heartRateZoneType,
                )
            )
            if existing is None:
                existing = HealthHeartRateZone(
                    connection_id=connection.id,
                    user_id=connection.user_id,
                    local_date=day,
                    zone_type=zone.heartRateZoneType,
                )
                db.add(existing)
            existing.min_bpm = zone.minBeatsPerMinute
            existing.max_bpm = zone.maxBeatsPerMinute
            existing.imported_at = datetime.now(timezone.utc)
        return
    elif isinstance(value, GoogleRespiratorySleepSummary):
        sample = value.sampleTime
        physical = sample.get("physicalTime")
        if not isinstance(physical, str):
            raise ValueError("Respiratory sample time missing")
        observed = datetime.fromisoformat(physical.replace("Z", "+00:00"))
        day = observed.date()
        _upsert_metric(
            db,
            connection,
            data_type,
            "sleep_respiratory_rate",
            value.fullSleepStats.breathsPerMinute,
            "breaths/min",
            day,
            source_id=source_id,
            observed_at=observed,
        )
        return
    else:
        raise ValueError("Unsupported normalized value")
    for metric_type, number, unit in metrics:
        _upsert_metric(db, connection, data_type, metric_type, number, unit, day, source_id=source_id)


def _sync_daily_rollups(
    db: Session,
    run: HealthSyncRun,
    connection: HealthConnection,
    client: GoogleHealthClient,
    access_token: str,
    start: datetime,
    end: datetime,
) -> None:
    for data_type, field_name, metric_type, value_key, unit in (
        ("steps", "steps", "steps", "countSum", "count"),
        ("active-energy-burned", "activeEnergyBurned", "active_calories", "kcalSum", "kcal"),
        ("total-calories", "totalCalories", "total_calories", "kcalSum", "kcal"),
    ):
        for chunk_start, chunk_end in _date_chunks(start.date(), end.date() + timedelta(days=1), 14):
            points = list(
                client.daily_rollup_data_points(
                    access_token, data_type, start=chunk_start, end=chunk_end
                )
            )
            run.fetched_count += len(points)
            for raw in points:
                try:
                    point = GoogleDailyRollupPoint.model_validate(raw)
                    values = getattr(point, field_name)
                    if values is None:
                        continue
                    raw_number = values.get(value_key)
                    if raw_number is None:
                        # Current v4 energy rollups may use kcal_sum or kcalSum.
                        raw_number = values.get("kcal_sum")
                    number = float(raw_number)
                    if not isfinite(number) or number < 0:
                        raise ValueError("Invalid daily rollup")
                    day = point.civilStartTime.date.as_date()
                    _upsert_metric(db, connection, data_type, metric_type, number, unit, day)
                    run.stored_count += 1
                except (ValidationError, ValueError, TypeError):
                    run.rejected_count += 1
        _advance_cursor(db, connection.id, data_type, end)
        db.commit()


def _sync_heart_rate(
    db: Session,
    run: HealthSyncRun,
    connection: HealthConnection,
    client: GoogleHealthClient,
    access_token: str,
    start: datetime,
    end: datetime,
) -> None:
    for chunk_start, chunk_end in _datetime_chunks(start, end, 14):
        for granularity, seconds in (("minute", 60), ("hour", 3600)):
            points = list(
                client.rollup_data_points(
                    access_token,
                    "heart-rate",
                    start=chunk_start,
                    end=chunk_end,
                    window_seconds=seconds,
                )
            )
            run.fetched_count += len(points)
            stored, rejected = store_physical_heart_rate_rollups(
                db,
                user_id=connection.user_id,
                connection_id=connection.id,
                granularity=granularity,
                points=points,
                timezone_name=get_settings().timezone,
            )
            run.stored_count += stored
            run.rejected_count += rejected
    daily_points: list[dict] = []
    for chunk_start, chunk_end in _date_chunks(start.date(), end.date() + timedelta(days=1), 14):
        daily_points.extend(
            client.daily_rollup_data_points(
                access_token, "heart-rate", start=chunk_start, end=chunk_end
            )
        )
    run.fetched_count += len(daily_points)
    stored, rejected = store_daily_heart_rate_rollups(
        db,
        user_id=connection.user_id,
        connection_id=connection.id,
        points=daily_points,
        timezone_name=get_settings().timezone,
    )
    run.stored_count += stored
    run.rejected_count += rejected
    _advance_cursor(db, connection.id, "heart-rate", end)
    db.commit()


def _sync_context_heart_rate(
    db: Session,
    run: HealthSyncRun,
    connection: HealthConnection,
    client: GoogleHealthClient,
    access_token: str,
    start: datetime,
    end: datetime,
) -> None:
    sessions = db.scalars(
        select(HealthSleepSession).where(
            HealthSleepSession.connection_id == connection.id,
            HealthSleepSession.end_at >= start,
            HealthSleepSession.start_at < end,
        )
    ).all()
    exercises = db.scalars(
        select(HealthExercise).where(
            HealthExercise.connection_id == connection.id,
            HealthExercise.end_at >= start,
            HealthExercise.start_at < end,
        )
    ).all()
    for granularity, items in (("sleep", sessions), ("exercise", exercises)):
        for item in items:
            seconds = max(1, int((_aware(item.end_at) - _aware(item.start_at)).total_seconds()))
            points = list(
                client.rollup_data_points(
                    access_token,
                    "heart-rate",
                    start=_aware(item.start_at),
                    end=_aware(item.end_at),
                    window_seconds=seconds,
                )
            )
            run.fetched_count += len(points)
            stored, rejected = store_physical_heart_rate_rollups(
                db,
                user_id=connection.user_id,
                connection_id=connection.id,
                granularity=granularity,
                points=points,
                timezone_name=get_settings().timezone,
                sleep_session_id=item.id if granularity == "sleep" else None,
                exercise_id=item.id if granularity == "exercise" else None,
            )
            run.stored_count += stored
            run.rejected_count += rejected
    db.commit()


def _store_sleep(
    db: Session,
    connection: HealthConnection,
    value: GoogleSleep,
    external_name: str | None,
    source_id: str | None,
) -> str:
    start = _aware(value.interval.startTime)
    end = _aware(value.interval.endTime)
    identity = external_name or f"{start.isoformat()}|{end.isoformat()}"
    dedupe = stable_hash("google-health-v4", "sleep", identity)
    session = db.scalar(
        select(HealthSleepSession).where(
            HealthSleepSession.connection_id == connection.id,
            HealthSleepSession.dedupe_hash == dedupe,
        )
    )
    if session is None:
        session = HealthSleepSession(
            connection_id=connection.id,
            user_id=connection.user_id,
            dedupe_hash=dedupe,
            start_at=start,
            end_at=end,
            local_date=_local_date(end, value.interval.civilEndTime),
        )
        db.add(session)
        db.flush()
    session.source_id = source_id
    session.start_at = start
    session.end_at = end
    session.start_utc_offset_seconds = _duration_seconds(value.interval.startUtcOffset)
    session.end_utc_offset_seconds = _duration_seconds(value.interval.endUtcOffset)
    session.sleep_type = value.type
    session.is_nap = value.metadata.nap
    session.processed = value.metadata.processed
    session.manually_edited = value.metadata.manuallyEdited
    session.stages_status = value.metadata.stagesStatus
    session.minutes_asleep = value.summary.minutesAsleep
    session.minutes_awake = value.summary.minutesAwake
    session.minutes_to_fall_asleep = value.summary.minutesToFallAsleep
    session.provider_updated_at = value.updateTime
    session.imported_at = datetime.now(timezone.utc)
    session.stages.clear()
    for stage in value.stages:
        session.stages.append(
            HealthSleepStage(
                start_at=_aware(stage.startTime),
                end_at=_aware(stage.endTime),
                start_utc_offset_seconds=_duration_seconds(stage.startUtcOffset),
                end_utc_offset_seconds=_duration_seconds(stage.endUtcOffset),
                stage_type=stage.type,
            )
        )
    return dedupe


def _store_exercise(
    db: Session,
    connection: HealthConnection,
    value: GoogleExercise,
    external_name: str | None,
    source_id: str | None,
) -> str:
    start = _aware(value.interval.startTime)
    end = _aware(value.interval.endTime)
    identity = external_name or f"{value.exerciseType}|{start.isoformat()}|{end.isoformat()}"
    dedupe = stable_hash("google-health-v4", "exercise", identity)
    exercise = db.scalar(
        select(HealthExercise).where(
            HealthExercise.connection_id == connection.id,
            HealthExercise.dedupe_hash == dedupe,
        )
    )
    if exercise is None:
        exercise = HealthExercise(
            connection_id=connection.id,
            user_id=connection.user_id,
            dedupe_hash=dedupe,
            start_at=start,
            end_at=end,
            local_date=_local_date(start, value.interval.civilStartTime),
            exercise_type=value.exerciseType,
        )
        db.add(exercise)
        db.flush()
    metrics = value.metricsSummary
    exercise.source_id = source_id
    exercise.start_at = start
    exercise.end_at = end
    exercise.start_utc_offset_seconds = _duration_seconds(value.interval.startUtcOffset)
    exercise.end_utc_offset_seconds = _duration_seconds(value.interval.endUtcOffset)
    exercise.exercise_type = value.exerciseType
    exercise.title = value.displayName
    exercise.active_duration_seconds = _duration_seconds(value.activeDuration) if value.activeDuration else None
    exercise.calories_kcal = metrics.caloriesKcal
    exercise.distance_m = metrics.distanceMillimeters / 1000 if metrics.distanceMillimeters is not None else None
    exercise.steps = metrics.steps
    exercise.average_heart_rate_bpm = metrics.averageHeartRateBeatsPerMinute
    exercise.active_zone_minutes = metrics.activeZoneMinutes
    exercise.heart_rate_zone_seconds = {
        key: _duration_seconds(raw)
        for key, raw in metrics.heartRateZoneDurations.items()
        if key in {"lightTime", "moderateTime", "vigorousTime", "peakTime"}
    }
    exercise.has_gps = value.exerciseMetadata.hasGps
    exercise.provider_updated_at = value.updateTime
    exercise.imported_at = datetime.now(timezone.utc)
    return dedupe


def _upsert_metric(
    db: Session,
    connection: HealthConnection,
    data_type: str,
    metric_type: str,
    value: float,
    unit: str,
    day: date,
    *,
    source_id: str | None = None,
    observed_at: datetime | None = None,
) -> None:
    number = float(value)
    if not isfinite(number):
        raise ValueError("Nicht endlicher Messwert")
    identity = observed_at.isoformat() if observed_at else day.isoformat()
    dedupe = stable_hash("google-health-v4", data_type, metric_type, identity)
    metric = db.scalar(
        select(HealthMetric).where(
            HealthMetric.connection_id == connection.id,
            HealthMetric.dedupe_hash == dedupe,
        )
    )
    if metric is None:
        metric = HealthMetric(
            connection_id=connection.id,
            user_id=connection.user_id,
            dedupe_hash=dedupe,
            data_type=data_type,
            metric_type=metric_type,
            local_date=day,
        )
        db.add(metric)
    metric.source_id = source_id
    metric.value = number
    metric.unit = unit
    metric.observed_at = observed_at
    metric.imported_at = datetime.now(timezone.utc)
    # A provider page can contain an exact duplicate. Flush the fully populated
    # identity so a second point in the same transaction updates this row.
    db.flush()


def _source_id(db: Session, connection_id: str, payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    device = payload.get("device") if isinstance(payload.get("device"), dict) else {}
    application = payload.get("application") if isinstance(payload.get("application"), dict) else {}
    whitelisted = {
        "recording_method": payload.get("recordingMethod"),
        "platform": payload.get("platform"),
        "device_manufacturer": _short(device.get("manufacturer"), 120),
        "device_name": _short(device.get("displayName"), 160),
        "device_form_factor": _short(device.get("formFactor"), 60),
        "application_name": _short(application.get("displayName"), 160),
    }
    fingerprint = hashlib.sha256(
        json.dumps(whitelisted, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    source = db.scalar(
        select(HealthDataSource).where(
            HealthDataSource.connection_id == connection_id,
            HealthDataSource.fingerprint == fingerprint,
        )
    )
    if source is None:
        source = HealthDataSource(connection_id=connection_id, fingerprint=fingerprint, **whitelisted)
        db.add(source)
        db.flush()
    source.last_seen_at = datetime.now(timezone.utc)
    return source.id


def _mark_sleep_overlaps(db: Session, connection: HealthConnection) -> None:
    sessions = db.scalars(
        select(HealthSleepSession)
        .where(HealthSleepSession.connection_id == connection.id)
        .order_by(HealthSleepSession.start_at)
    ).all()
    for session in sessions:
        session.overlaps_other_session = False
    for previous, current in zip(sessions, sessions[1:]):
        if _aware(current.start_at) < _aware(previous.end_at):
            previous.overlaps_other_session = current.overlaps_other_session = True


def _refresh_gaps(db: Session, connection: HealthConnection, start: date, end: date) -> None:
    db.execute(
        delete(HealthDataGap).where(
            HealthDataGap.connection_id == connection.id,
            HealthDataGap.local_date >= start,
            HealthDataGap.local_date <= end,
        )
    )
    metrics = db.scalars(
        select(HealthMetric).where(
            HealthMetric.connection_id == connection.id,
            HealthMetric.local_date >= start,
            HealthMetric.local_date <= end,
        )
    ).all()
    sleeps = db.scalars(
        select(HealthSleepSession).where(
            HealthSleepSession.connection_id == connection.id,
            HealthSleepSession.local_date >= start,
            HealthSleepSession.local_date <= end,
        )
    ).all()
    present: dict[str, set[date]] = {
        "steps": {item.local_date for item in metrics if item.metric_type == "steps" and item.local_date},
        "sleep": {item.local_date for item in sleeps},
        "recovery": {
            item.local_date
            for item in metrics
            if item.metric_type in {"hrv_rmssd", "resting_heart_rate"} and item.local_date
        },
    }
    current = start
    while current <= end:
        for data_type, dates in present.items():
            if current not in dates:
                db.add(
                    HealthDataGap(
                        connection_id=connection.id,
                        user_id=connection.user_id,
                        data_type=data_type,
                        local_date=current,
                        reason="missing",
                    )
                )
        current += timedelta(days=1)


def _advance_cursor(db: Session, connection_id: str, data_type: str, end: datetime) -> None:
    cursor = db.scalar(
        select(HealthSyncCursor).where(
            HealthSyncCursor.connection_id == connection_id,
            HealthSyncCursor.data_type == data_type,
        )
    )
    if cursor is None:
        cursor = HealthSyncCursor(connection_id=connection_id, data_type=data_type)
        db.add(cursor)
    cursor.completed_through = end
    cursor.last_attempt_at = cursor.last_success_at = datetime.now(timezone.utc)
    cursor.last_error_code = None


def _delete_stale_sessions(
    db: Session, connection_id: str, start: datetime, end: datetime, seen: set[str]
) -> None:
    query = select(HealthSleepSession).where(
        HealthSleepSession.connection_id == connection_id,
        HealthSleepSession.end_at >= start,
        HealthSleepSession.start_at < end,
    )
    for item in db.scalars(query).all():
        if item.dedupe_hash not in seen:
            db.delete(item)


def _delete_stale_exercises(
    db: Session, connection_id: str, start: datetime, end: datetime, seen: set[str]
) -> None:
    query = select(HealthExercise).where(
        HealthExercise.connection_id == connection_id,
        HealthExercise.end_at >= start,
        HealthExercise.start_at < end,
    )
    for item in db.scalars(query).all():
        if item.dedupe_hash not in seen:
            db.delete(item)


def _filter_for(data_type: str, start: datetime, end: datetime) -> str:
    start_z = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    end_z = end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    snake = data_type.replace("-", "_")
    if data_type in DAILY_DATA_TYPES:
        return f'{snake}.date >= "{start.date().isoformat()}" AND {snake}.date < "{(end.date() + timedelta(days=1)).isoformat()}"'
    if data_type == "sleep":
        return f'sleep.interval.end_time >= "{start_z}" AND sleep.interval.end_time < "{end_z}"'
    if data_type == "exercise":
        return f'exercise.interval.civil_start_time >= "{start.date().isoformat()}" AND exercise.interval.civil_start_time < "{(end.date() + timedelta(days=1)).isoformat()}"'
    if data_type == "respiratory-rate-sleep-summary":
        return f'{snake}.sample_time.physical_time >= "{start_z}" AND {snake}.sample_time.physical_time < "{end_z}"'
    raise ValueError("Unsupported filter data type")


def _duration_seconds(value: str | None) -> float:
    if not value or not re.fullmatch(r"-?\d+(?:\.\d+)?s", value):
        raise ValueError("Ungültige Protobuf-Dauer")
    result = float(value[:-1])
    if not isfinite(result) or abs(result) > 10 * 365 * 24 * 3600:
        raise ValueError("Ungültige Protobuf-Dauer")
    return result


def _local_date(instant: datetime, civil: Any | None) -> date:
    if civil is not None:
        return civil.date.as_date()
    return instant.astimezone(ZoneInfo(get_settings().timezone)).date()


def _optional_metrics(*values: tuple[str, float | int | None, str]) -> list[tuple[str, float, str]]:
    return [(name, float(value), unit) for name, value, unit in values if value is not None]


def _date_chunks(start: date, end: date, days: int):
    current = start
    while current < end:
        following = min(end, current + timedelta(days=days))
        yield current, following
        current = following


def _datetime_chunks(start: datetime, end: datetime, days: int):
    current = start
    while current < end:
        following = min(end, current + timedelta(days=days))
        yield current, following
        current = following


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _short(value: Any, maximum: int) -> str | None:
    return value[:maximum] if isinstance(value, str) and value else None
