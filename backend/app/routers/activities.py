from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..ai import LocalSummaryProvider, get_summary_provider
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, User, utcnow
from ..schemas import (
    ActivityListResponse,
    ActivityResponse,
    ActivityUpdate,
    CompareRequest,
    CompareResponse,
    StatisticsOverview,
    SummaryResponse,
    TrackResponse,
    WeatherResponse,
)
from ..tcx import TcxError, parse_tcx
from ..weather import get_weather_provider


router = APIRouter(tags=["Aktivitäten"])


def _activity_for_user(db: Session, user: User, activity_id: str) -> Activity:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id))
    if activity is None:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden.")
    return activity


def _activity_response(activity: Activity) -> ActivityResponse:
    return ActivityResponse(
        id=activity.id,
        title=activity.title,
        type=activity.activity_type,
        notes=activity.notes,
        original_filename=activity.original_filename,
        started_at=activity.started_at,
        ended_at=activity.ended_at,
        distance_m=activity.distance_m,
        duration_s=activity.duration_s,
        moving_time_s=activity.moving_time_s,
        pause_time_s=activity.pause_time_s,
        avg_speed_mps=activity.avg_speed_mps,
        max_speed_mps=activity.max_speed_mps,
        elevation_gain_m=activity.elevation_gain_m,
        avg_hr_bpm=activity.avg_hr_bpm,
        max_hr_bpm=activity.max_hr_bpm,
        avg_cadence_rpm=activity.avg_cadence_rpm,
        max_cadence_rpm=activity.max_cadence_rpm,
        avg_power_w=activity.avg_power_w,
        max_power_w=activity.max_power_w,
        training_load=activity.training_load,
        hr_zone_seconds=activity.hr_zone_seconds or {},
        weather=activity.weather,
        weather_status=activity.weather_status,
        ai_summary=activity.ai_summary,
        ai_provider=activity.ai_provider,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )


def _first_coordinate(activity: Activity) -> tuple[float, float] | None:
    for point in activity.track_points or []:
        if point.get("latitude") is not None and point.get("longitude") is not None:
            return float(point["latitude"]), float(point["longitude"])
    return None


def _refresh_weather(activity: Activity) -> None:
    settings = get_settings()
    coordinate = _first_coordinate(activity)
    if coordinate is None:
        activity.weather = None
        activity.weather_status = "unavailable"
        activity.weather_updated_at = utcnow()
        return
    provider = get_weather_provider(settings)
    try:
        activity.weather = provider.weather_at(*coordinate, activity.started_at)
        activity.weather_status = "available" if activity.weather else "unavailable"
    except Exception:
        activity.weather = None
        activity.weather_status = "unavailable"
    activity.weather_updated_at = utcnow()


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def upload_activity(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=200),
    type: str | None = Form(default=None, max_length=50),
    notes: str | None = Form(default=None, max_length=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityResponse:
    settings = get_settings()
    data = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=400, detail="Die hochgeladene Datei ist leer.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Die TCX-Datei ist zu groß.")
    digest = hashlib.sha256(data).hexdigest()
    duplicate = db.scalar(select(Activity).where(Activity.user_id == current_user.id, Activity.file_hash == digest))
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail={"message": "Diese TCX-Datei wurde bereits importiert.", "activity_id": duplicate.id},
        )
    try:
        parsed = parse_tcx(data, current_user.hr_zones or [], current_user.hr_max)
    except TcxError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    original_filename = (Path(file.filename or "activity.tcx").name or "activity.tcx")[:255]
    upload_directory = settings.upload_dir / current_user.id
    upload_directory.mkdir(parents=True, exist_ok=True)
    destination = upload_directory / f"{digest}.tcx"
    destination.write_bytes(data)
    activity = Activity(
        user_id=current_user.id,
        file_hash=digest,
        original_filename=original_filename,
        original_file_path=str(destination),
        title=(title.strip() if title and title.strip() else f"Radfahrt am {parsed.started_at:%d.%m.%Y}"),
        activity_type=(type.strip().lower() if type and type.strip() else parsed.activity_type),
        notes=notes.strip() if notes and notes.strip() else None,
        started_at=parsed.started_at,
        ended_at=parsed.ended_at,
        distance_m=parsed.distance_m,
        duration_s=parsed.duration_s,
        moving_time_s=parsed.moving_time_s,
        pause_time_s=parsed.pause_time_s,
        avg_speed_mps=parsed.avg_speed_mps,
        max_speed_mps=parsed.max_speed_mps,
        elevation_gain_m=parsed.elevation_gain_m,
        avg_hr_bpm=parsed.avg_hr_bpm,
        max_hr_bpm=parsed.max_hr_bpm,
        avg_cadence_rpm=parsed.avg_cadence_rpm,
        max_cadence_rpm=parsed.max_cadence_rpm,
        avg_power_w=parsed.avg_power_w,
        max_power_w=parsed.max_power_w,
        training_load=parsed.training_load,
        hr_zone_seconds=parsed.hr_zone_seconds,
        track_points=parsed.track_points,
    )
    _refresh_weather(activity)
    db.add(activity)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="Diese TCX-Datei wurde bereits importiert.") from None
    db.refresh(activity)
    return _activity_response(activity)


@router.get("/activities", response_model=ActivityListResponse)
def list_activities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200),
    type: str | None = Query(default=None, max_length=50),
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityListResponse:
    conditions: list[Any] = [Activity.user_id == current_user.id]
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(or_(Activity.title.ilike(pattern), Activity.notes.ilike(pattern)))
    if type:
        conditions.append(Activity.activity_type == type.strip().lower())
    if date_from:
        conditions.append(Activity.started_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(Activity.started_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    total = db.scalar(select(func.count()).select_from(Activity).where(*conditions)) or 0
    activities = db.scalars(
        select(Activity).where(*conditions).order_by(Activity.started_at.desc()).offset(offset).limit(limit)
    ).all()
    return ActivityListResponse(
        items=[_activity_response(activity) for activity in activities], total=total, limit=limit, offset=offset
    )


@router.post("/activities/compare", response_model=CompareResponse)
def compare_activities(
    payload: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompareResponse:
    requested = list(dict.fromkeys(payload.activity_ids))
    if len(requested) < 2:
        raise HTTPException(status_code=422, detail="Mindestens zwei unterschiedliche Aktivitäten sind erforderlich.")
    found = db.scalars(select(Activity).where(Activity.user_id == current_user.id, Activity.id.in_(requested))).all()
    by_id = {activity.id: activity for activity in found}
    if len(by_id) != len(requested):
        raise HTTPException(status_code=404, detail="Mindestens eine Aktivität wurde nicht gefunden.")
    return CompareResponse(activities=[_activity_response(by_id[activity_id]) for activity_id in requested])


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
def get_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityResponse:
    return _activity_response(_activity_for_user(db, current_user, activity_id))


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def update_activity(
    activity_id: str,
    payload: ActivityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("title") is not None:
        activity.title = values["title"].strip()
    if values.get("type") is not None:
        activity.activity_type = values["type"].strip().lower()
    if "notes" in values:
        activity.notes = values["notes"].strip() if values["notes"] and values["notes"].strip() else None
    db.commit()
    db.refresh(activity)
    return _activity_response(activity)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    activity = _activity_for_user(db, current_user, activity_id)
    file_path = Path(activity.original_file_path)
    db.delete(activity)
    db.commit()
    file_path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/activities/{activity_id}/track", response_model=TrackResponse)
def get_track(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrackResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    return TrackResponse(activity_id=activity.id, points=activity.track_points or [])


@router.get("/activities/{activity_id}/weather", response_model=WeatherResponse)
def get_weather(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeatherResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    return WeatherResponse(status=activity.weather_status, data=activity.weather, updated_at=activity.weather_updated_at)


@router.post("/activities/{activity_id}/weather/refresh", response_model=WeatherResponse)
def refresh_weather(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeatherResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    _refresh_weather(activity)
    db.commit()
    db.refresh(activity)
    return WeatherResponse(status=activity.weather_status, data=activity.weather, updated_at=activity.weather_updated_at)


def _generate_summary(activity: Activity) -> None:
    settings = get_settings()
    provider = get_summary_provider(settings)
    try:
        summary = provider.summarize(activity)
        provider_name = provider.name
    except Exception:
        summary = LocalSummaryProvider().summarize(activity)
        provider_name = "local_fallback"
    activity.ai_summary = summary
    activity.ai_provider = provider_name
    activity.ai_updated_at = utcnow()


@router.get("/activities/{activity_id}/summary", response_model=SummaryResponse)
def get_summary(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    if not activity.ai_summary or not activity.ai_provider or not activity.ai_updated_at:
        _generate_summary(activity)
        db.commit()
        db.refresh(activity)
    return SummaryResponse(summary=activity.ai_summary, provider=activity.ai_provider, updated_at=activity.ai_updated_at)


@router.post("/activities/{activity_id}/summary", response_model=SummaryResponse)
def create_summary(
    activity_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    activity = _activity_for_user(db, current_user, activity_id)
    if force or not activity.ai_summary:
        _generate_summary(activity)
        db.commit()
        db.refresh(activity)
    return SummaryResponse(summary=activity.ai_summary, provider=activity.ai_provider, updated_at=activity.ai_updated_at)


@router.get("/statistics/overview", response_model=StatisticsOverview)
def statistics_overview(
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatisticsOverview:
    conditions: list[Any] = [Activity.user_id == current_user.id]
    if date_from:
        conditions.append(Activity.started_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(Activity.started_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    activities = db.scalars(select(Activity).where(*conditions).order_by(Activity.started_at)).all()
    monthly: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"activity_count": 0, "distance_m": 0.0, "duration_s": 0.0, "elevation_gain_m": 0.0, "training_load": 0.0}
    )
    for activity in activities:
        key = activity.started_at.strftime("%Y-%m")
        monthly[key]["activity_count"] += 1
        monthly[key]["distance_m"] += activity.distance_m
        monthly[key]["duration_s"] += activity.duration_s
        monthly[key]["elevation_gain_m"] += activity.elevation_gain_m
        monthly[key]["training_load"] += activity.training_load
    distance = sum(activity.distance_m for activity in activities)
    moving = sum(activity.moving_time_s for activity in activities)
    return StatisticsOverview(
        activity_count=len(activities),
        distance_m=round(distance, 2),
        duration_s=round(sum(activity.duration_s for activity in activities), 2),
        moving_time_s=round(moving, 2),
        elevation_gain_m=round(sum(activity.elevation_gain_m for activity in activities), 2),
        training_load=round(sum(activity.training_load for activity in activities), 2),
        avg_speed_mps=round(distance / moving, 3) if moving else 0.0,
        by_month=[{"month": month, **{key: round(value, 2) if isinstance(value, float) else value for key, value in values.items()}} for month, values in sorted(monthly.items())],
    )
