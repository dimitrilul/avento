from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import RefreshToken, User, utcnow
from ..schemas import ProfilePasswordChange, ProfileResponse, ProfileUpdate
from ..security import hash_password, verify_password
from ..tcx import default_hr_zones


router = APIRouter(prefix="/profile", tags=["Profil"])


def _validate_zones(zones: list[dict]) -> None:
    ordered = sorted(zones, key=lambda zone: zone["min_bpm"])
    for index, zone in enumerate(ordered):
        if zone["min_bpm"] > zone["max_bpm"]:
            raise HTTPException(status_code=422, detail="Eine Herzfrequenzzone hat ungültige Grenzen.")
        if index and zone["min_bpm"] <= ordered[index - 1]["max_bpm"]:
            raise HTTPException(status_code=422, detail="Herzfrequenzzonen dürfen sich nicht überschneiden.")


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
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
    if current_user.hr_rest >= current_user.hr_max:
        raise HTTPException(status_code=422, detail="Der Ruhepuls muss unter dem Maximalpuls liegen.")
    db.commit()
    db.refresh(current_user)
    return current_user


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
