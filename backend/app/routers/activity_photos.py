from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..database import get_db
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
    validate_and_store_photo,
)
from ..schemas import ActivityPhotoListResponse, ActivityPhotoResponse, ActivityPhotoUpdate


router = APIRouter(tags=["Aktivitätsfotos"])


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
        width=photo.width,
        height=photo.height,
        captured_at=_utc(photo.captured_at),
        latitude=photo.latitude,
        longitude=photo.longitude,
        caption=photo.caption,
        file_url=f"/api/v1/activities/{photo.activity_id}/photos/{photo.id}/file",
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
        stored = await run_in_threadpool(
            validate_and_store_photo,
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
        storage_path=str(stored.path),
        original_filename=original_filename,
        content_type=stored.content_type,
        file_hash=stored.file_hash,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
        captured_at=(captured_at or stored.captured_at).astimezone(timezone.utc)
        if (captured_at or stored.captured_at)
        else None,
        latitude=latitude if latitude is not None else stored.latitude,
        longitude=longitude if longitude is not None else stored.longitude,
        caption=normalized_caption,
    )
    db.add(photo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        staged = stage_photo_deletions([stored.path], settings.upload_dir)
        finalize_staged_photo_deletions(staged)
        raise HTTPException(status_code=409, detail="Dieses Foto ist für die Aktivität bereits vorhanden.") from None
    except Exception:
        db.rollback()
        staged = stage_photo_deletions([stored.path], settings.upload_dir)
        finalize_staged_photo_deletions(staged)
        raise
    db.refresh(photo)
    return _photo_response(photo)


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
    try:
        path = safe_photo_path(photo.storage_path, get_settings().upload_dir, must_exist=True)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Die Fotodatei ist nicht verfügbar.") from exc
    return FileResponse(
        path,
        media_type=photo.content_type,
        filename=f"{photo.id}.webp",
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=3600",
            "ETag": f'"{photo.file_hash}"',
            "X-Content-Type-Options": "nosniff",
        },
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
        staged = stage_photo_deletions([photo.storage_path], settings.upload_dir)
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
