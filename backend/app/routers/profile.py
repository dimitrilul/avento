from __future__ import annotations

import base64
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, RefreshToken, User, utcnow
from ..schemas import ProfilePasswordChange, ProfileResponse, ProfileUpdate
from ..security import hash_password, verify_password
from ..tcx import default_hr_zones


router = APIRouter(prefix="/profile", tags=["Profil"])


def _avatar_data_url(user: User) -> str | None:
    if not user.avatar_path:
        return None
    try:
        data = Path(user.avatar_path).read_bytes()
    except OSError:
        return None
    return f"data:image/webp;base64,{base64.b64encode(data).decode('ascii')}"


def _profile_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        hr_max=user.hr_max,
        hr_rest=user.hr_rest,
        hr_zones=user.hr_zones or [],
        training_goals=user.training_goals or [],
        avatar_data_url=_avatar_data_url(user),
    )


def _store_avatar(data: bytes, user_id: str) -> Path:
    settings = get_settings()
    with Image.open(BytesIO(data)) as source:
        if source.width <= 0 or source.height <= 0 or source.width * source.height > settings.max_avatar_pixels:
            raise ValueError("Das Bild hat zu viele Pixel.")
        source.load()
        image = ImageOps.exif_transpose(source)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA")
        image = ImageOps.fit(
            image,
            (settings.avatar_size_px, settings.avatar_size_px),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        avatar_dir = settings.upload_dir / user_id / "profile"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        destination = avatar_dir / "avatar.webp"
        temporary = avatar_dir / f"avatar-{uuid.uuid4().hex}.tmp"
        try:
            image.save(temporary, format="WEBP", quality=88, method=6)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def _validate_zones(zones: list[dict]) -> None:
    ordered = sorted(zones, key=lambda zone: zone["min_bpm"])
    for index, zone in enumerate(ordered):
        if zone["min_bpm"] > zone["max_bpm"]:
            raise HTTPException(status_code=422, detail="Eine Herzfrequenzzone hat ungültige Grenzen.")
        if index and zone["min_bpm"] <= ordered[index - 1]["max_bpm"]:
            raise HTTPException(status_code=422, detail="Herzfrequenzzonen dürfen sich nicht überschneiden.")


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return _profile_response(current_user)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    values = payload.model_dump(exclude_unset=True)
    if values.get("display_name") is not None:
        current_user.display_name = values["display_name"].strip()
    if values.get("hr_rest") is not None:
        current_user.hr_rest = values["hr_rest"]
    if values.get("hr_max") is not None:
        current_user.hr_max = values["hr_max"]
        if "hr_zones" not in values:
            current_user.hr_zones = default_hr_zones(current_user.hr_max)
    if values.get("hr_zones") is not None:
        serialized = [zone.model_dump() if hasattr(zone, "model_dump") else zone for zone in values["hr_zones"]]
        _validate_zones(serialized)
        current_user.hr_zones = serialized
    if values.get("training_goals") is not None:
        current_user.training_goals = values["training_goals"]
    if current_user.hr_rest >= current_user.hr_max:
        raise HTTPException(status_code=422, detail="Der Ruhepuls muss unter dem Maximalpuls liegen.")
    if {"hr_rest", "hr_max", "hr_zones", "training_goals"}.intersection(values):
        db.execute(
            update(Activity)
            .where(Activity.user_id == current_user.id)
            .values(ai_summary=None, ai_provider=None, ai_data_basis=None, ai_updated_at=None)
        )
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user)


@router.post("/avatar", response_model=ProfileResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    settings = get_settings()
    data = await file.read(settings.max_avatar_bytes + 1)
    await file.close()
    if not data:
        raise HTTPException(status_code=400, detail="Die Bilddatei ist leer.")
    if len(data) > settings.max_avatar_bytes:
        raise HTTPException(status_code=413, detail="Das Profilbild darf höchstens 10 MB groß sein.")
    try:
        destination = await run_in_threadpool(_store_avatar, data, current_user.id)
    except (UnidentifiedImageError, Image.DecompressionBombError, MemoryError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Das Bildformat wird nicht unterstützt oder die Datei ist beschädigt.",
        ) from exc
    current_user.avatar_path = str(destination)
    current_user.avatar_updated_at = utcnow()
    db.commit()
    db.refresh(current_user)
    return _profile_response(current_user)


@router.delete("/avatar", response_model=ProfileResponse)
def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    avatar_path = Path(current_user.avatar_path) if current_user.avatar_path else None
    current_user.avatar_path = None
    current_user.avatar_updated_at = utcnow()
    db.commit()
    db.refresh(current_user)
    if avatar_path:
        avatar_path.unlink(missing_ok=True)
    return _profile_response(current_user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ProfilePasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Das aktuelle Passwort ist falsch.")
    now = utcnow()
    current_user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
