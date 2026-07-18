from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Activity, ActivityPhoto, User, uuid4_str
from ..photo_storage import (
    MAX_PHOTO_BYTES,
    MAX_PHOTOS_PER_ACTIVITY,
    PhotoValidationError,
    finalize_staged_photo_deletions,
    restore_staged_photo_deletions,
    safe_photo_path,
    stage_photo_deletions,
    validate_and_store_original,
    create_optimized_photo,
)
from ..schemas import ActivityPhotoListResponse, ActivityPhotoResponse, ActivityPhotoUpdate


router = APIRouter(tags=["Aktivitätsfotos"])
logger = logging.getLogger(__name__)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _activity_for_user(db: Session, user: User, activity_id: str) -> Activity:
    activity = db.scalar(select(Activity).where(Activity.id == activity_id, Activity.user_id == user.id))
    if activity is None:
        raise HTTPException(status_code=404, detail="Aktivität nicht gefunden.")
    return activity


def _photo_for_user(db: Session, user: User, activity_id: str, photo_id: str) -> ActivityPhoto:
    photo = db.scalar(
        select(ActivityPhoto).where(
            ActivityPhoto.id == photo_id,
            ActivityPhoto.activity_id == activity_id,
            ActivityPhoto.user_id == user.id,
        )
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Aktivitätsfoto nicht gefunden.")
    return photo


def _photo_response(photo: ActivityPhoto) -> ActivityPhotoResponse:
    return ActivityPhotoResponse(
        id=photo.id,
        activity_id=photo.activity_id,
        original_filename=photo.original_filename,
        content_type=photo.content_type,
        size_bytes=photo.size_bytes,
        original_size_bytes=photo.original_size_bytes,
        width=photo.width,
        height=photo.height,
        captured_at=_utc(photo.captured_at),
        latitude=photo.latitude,
        longitude=photo.longitude,
        caption=photo.caption,
        file_url=f"/api/v1/activities/{photo.activity_id}/photos/{photo.id}/file",
        original_file_url=f"/api/v1/activities/{photo.activity_id}/photos/{photo.id}/original",
        processing_status=photo.processing_status,
        created_at=photo.created_at,
        updated_at=photo.updated_at,
    )


@router.post(
    "/activities/{activity_id}/photos",
    response_model=ActivityPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_activity_photo(
    activity_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    captured_at: datetime | None = Form(default=None),
    latitude: float | None = Form(default=None, ge=-90, le=90),
    longitude: float | None = Form(default=None, ge=-180, le=180),
    client_timezone: str | None = Form(default=None, max_length=100),
    caption: str | None = Form(default=None, max_length=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityPhotoResponse:
    _activity_for_user(db, current_user, activity_id)
    if captured_at is not None and (captured_at.tzinfo is None or captured_at.utcoffset() is None):
        raise HTTPException(status_code=422, detail="captured_at muss eine Zeitzone enthalten.")
    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=422, detail="Breiten- und Längengrad müssen gemeinsam angegeben werden.")
    assumed_timezone = None
    if client_timezone:
        try:
            assumed_timezone = ZoneInfo(client_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(status_code=422, detail="client_timezone ist keine gültige IANA-Zeitzone.") from None
    photo_count = db.scalar(
        select(func.count()).select_from(ActivityPhoto).where(
            ActivityPhoto.activity_id == activity_id,
            ActivityPhoto.user_id == current_user.id,
        )
    ) or 0
    if photo_count >= MAX_PHOTOS_PER_ACTIVITY:
        raise HTTPException(
            status_code=409,
            detail=f"Pro Aktivität sind höchstens {MAX_PHOTOS_PER_ACTIVITY} Fotos erlaubt.",
        )

    data = await file.read(MAX_PHOTO_BYTES + 1)
    original_filename = (Path(file.filename or "photo").name or "photo")[:255]
    await file.close()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Das Aktivitätsfoto ist zu groß.")
    digest = hashlib.sha256(data).hexdigest()
    duplicate = db.scalar(
        select(ActivityPhoto.id).where(
            ActivityPhoto.activity_id == activity_id,
            ActivityPhoto.user_id == current_user.id,
            ActivityPhoto.file_hash == digest,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Dieses Foto ist für die Aktivität bereits vorhanden.")

    settings = get_settings()
    photo_id = uuid4_str()
    try:
        original = await run_in_threadpool(
            validate_and_store_original,
            data,
            photo_id,
            settings.upload_dir,
            assumed_timezone,
        )
    except PhotoValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    normalized_caption = caption.strip() if caption and caption.strip() else None
    photo = ActivityPhoto(
        id=photo_id,
        activity_id=activity_id,
        user_id=current_user.id,
        original_storage_path=str(original.path),
        original_content_type=original.content_type,
        original_size_bytes=original.size_bytes,
        storage_path=None,
        original_filename=original_filename,
        content_type="image/webp",
        file_hash=original.file_hash,
        size_bytes=original.size_bytes,
        width=original.width,
        height=original.height,
        captured_at=(captured_at or original.captured_at).astimezone(timezone.utc)
        if (captured_at or original.captured_at)
        else None,
        latitude=latitude if latitude is not None else original.latitude,
        longitude=longitude if longitude is not None else original.longitude,
        caption=normalized_caption,
        processing_status="pending",
    )
    db.add(photo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        staged = stage_photo_deletions([original.path], settings.upload_dir)
        finalize_staged_photo_deletions(staged)
        raise HTTPException(status_code=409, detail="Dieses Foto ist für die Aktivität bereits vorhanden.") from None
    except Exception:
        db.rollback()
        staged = stage_photo_deletions([original.path], settings.upload_dir)
        finalize_staged_photo_deletions(staged)
        raise
    db.refresh(photo)
    background_tasks.add_task(_optimize_photo_in_background, photo.id)
    return _photo_response(photo)


def _optimize_photo_in_background(photo_id: str) -> None:
    db = SessionLocal()
    try:
        photo = db.get(ActivityPhoto, photo_id)
        if photo is None:
            return
        photo.processing_status = "processing"
        db.commit()
        settings = get_settings()
        original_path = safe_photo_path(photo.original_storage_path, settings.upload_dir, must_exist=True)
        optimized = create_optimized_photo(original_path, photo.id, settings.upload_dir)
        photo.storage_path = str(optimized.path)
        photo.content_type = optimized.content_type
        photo.size_bytes = optimized.size_bytes
        photo.width = optimized.width
        photo.height = optimized.height
        photo.processing_status = "ready"
        db.commit()
    except Exception:
        db.rollback()
        photo = db.get(ActivityPhoto, photo_id)
        if photo is not None:
            photo.processing_status = "failed"
            db.commit()
        logger.exception("Optimierung des Aktivitätsfotos %s fehlgeschlagen", photo_id)
    finally:
        db.close()


@router.get("/activities/{activity_id}/photos", response_model=ActivityPhotoListResponse)
def list_activity_photos(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityPhotoListResponse:
    _activity_for_user(db, current_user, activity_id)
    photos = db.scalars(
        select(ActivityPhoto)
        .where(ActivityPhoto.activity_id == activity_id, ActivityPhoto.user_id == current_user.id)
        .order_by(ActivityPhoto.captured_at.desc(), ActivityPhoto.created_at.desc())
    ).all()
    return ActivityPhotoListResponse(items=[_photo_response(photo) for photo in photos], total=len(photos))


@router.patch(
    "/activities/{activity_id}/photos/{photo_id}",
    response_model=ActivityPhotoResponse,
)
def update_activity_photo(
    activity_id: str,
    photo_id: str,
    payload: ActivityPhotoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActivityPhotoResponse:
    _activity_for_user(db, current_user, activity_id)
    photo = _photo_for_user(db, current_user, activity_id, photo_id)
    values = payload.model_dump(exclude_unset=True)
    resulting_latitude = values.get("latitude", photo.latitude)
    resulting_longitude = values.get("longitude", photo.longitude)
    if (resulting_latitude is None) != (resulting_longitude is None):
        raise HTTPException(status_code=422, detail="Breiten- und Längengrad müssen gemeinsam angegeben werden.")
    if "captured_at" in values:
        photo.captured_at = values["captured_at"].astimezone(timezone.utc) if values["captured_at"] else None
    if "latitude" in values:
        photo.latitude = values["latitude"]
    if "longitude" in values:
        photo.longitude = values["longitude"]
    if "caption" in values:
        photo.caption = values["caption"].strip() if values["caption"] and values["caption"].strip() else None
    db.commit()
    db.refresh(photo)
    return _photo_response(photo)


@router.get("/activities/{activity_id}/photos/{photo_id}/file", response_class=FileResponse)
def get_activity_photo_file(
    activity_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    _activity_for_user(db, current_user, activity_id)
    photo = _photo_for_user(db, current_user, activity_id, photo_id)
    settings = get_settings()
    optimized = bool(photo.storage_path)
    try:
        path = safe_photo_path(photo.storage_path, settings.upload_dir, must_exist=True) if optimized else safe_photo_path(photo.original_storage_path, settings.upload_dir, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Die Fotodatei ist nicht verfügbar.") from exc
    return FileResponse(
        path,
        media_type=photo.content_type if optimized else photo.original_content_type,
        filename=f"{photo.id}.webp" if optimized else photo.original_filename,
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=3600",
            "ETag": f'"{photo.file_hash}-{photo.processing_status}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/activities/{activity_id}/photos/{photo_id}/original", response_class=FileResponse)
def get_activity_photo_original(
    activity_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    _activity_for_user(db, current_user, activity_id)
    photo = _photo_for_user(db, current_user, activity_id, photo_id)
    try:
        path = safe_photo_path(photo.original_storage_path, get_settings().upload_dir, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Die Originaldatei ist nicht verfügbar.") from exc
    return FileResponse(
        path,
        media_type=photo.original_content_type,
        filename=photo.original_filename,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=3600", "ETag": f'"{photo.file_hash}-original"', "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/activities/{activity_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity_photo(
    activity_id: str,
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    _activity_for_user(db, current_user, activity_id)
    photo = _photo_for_user(db, current_user, activity_id, photo_id)
    settings = get_settings()
    try:
        staged = stage_photo_deletions(
            [path for path in (photo.storage_path, photo.original_storage_path) if path], settings.upload_dir
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Die Fotodatei konnte nicht sicher entfernt werden.") from exc
    db.delete(photo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        restore_staged_photo_deletions(staged)
        raise
    finalize_staged_photo_deletions(staged)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
