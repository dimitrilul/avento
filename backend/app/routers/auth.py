from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Invitation, PasswordResetToken, RefreshToken, User, utcnow
from ..schemas import (
    BootstrapRequest,
    InvitationCreate,
    InvitationResponse,
    LoginRequest,
    PasswordResetCreate,
    PasswordResetCreated,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    Login2FARequest, LoginChallengeResponse, PasskeyNameRequest, TotpSetupResponse,
)
from ..mcp_security import revoke_oauth_user_tokens
from ..security import (
    create_access_token, create_factor_challenge, decrypt_factor_secret, encrypt_factor_secret,
    generate_opaque_token, generate_totp_secret, hash_password, token_hash, totp_uri, verify_password, verify_totp,
)
from ..passkeys import authenticate_credential, authentication_options, register_credential, registration_options
from jwt import InvalidTokenError
from ..tcx import default_hr_zones


router = APIRouter(prefix="/auth", tags=["Authentifizierung"])


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    access_token, expires_in = create_access_token(user.id)
    refresh_value = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash(refresh_value),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_value, expires_in=expires_in)


@router.get("/bootstrap/status")
def bootstrap_status(db: Session = Depends(get_db)) -> dict[str, bool]:
    count = db.scalar(select(func.count()).select_from(User)) or 0
    return {"available": count == 0}


@router.post("/bootstrap", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(payload: BootstrapRequest, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    if settings.bootstrap_invite_code:
        if payload.bootstrap_code is None or not secrets.compare_digest(
            payload.bootstrap_code, settings.bootstrap_invite_code
        ):
            raise HTTPException(status_code=403, detail="Der Bootstrap-Code ist ungültig.")
    elif settings.environment.lower() not in {"development", "test"}:
        raise HTTPException(status_code=503, detail="Der sichere Bootstrap ist nicht konfiguriert.")
    if (db.scalar(select(func.count()).select_from(User)) or 0) > 0:
        raise HTTPException(status_code=409, detail="Der erste Benutzer wurde bereits eingerichtet.")
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        is_admin=True,
        hr_zones=default_hr_zones(190),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Der erste Benutzer wurde bereits eingerichtet.") from None
    return _issue_tokens(db, user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    invitation = db.scalar(select(Invitation).where(Invitation.token_hash == token_hash(payload.invite_token)))
    now = utcnow()
    if invitation is None or invitation.used_at is not None or _aware(invitation.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Die Einladung ist ungültig oder abgelaufen.")
    email = str(payload.email).lower()
    if invitation.email and invitation.email.lower() != email:
        raise HTTPException(status_code=400, detail="Die Einladung wurde für eine andere E-Mail-Adresse erstellt.")
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=409, detail="Für diese E-Mail-Adresse existiert bereits ein Konto.")
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        hr_zones=default_hr_zones(190),
    )
    invitation.used_at = now
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Für diese E-Mail-Adresse existiert bereits ein Konto.") from None
    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenResponse | LoginChallengeResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse | LoginChallengeResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-Mail-Adresse oder Passwort ist falsch.")
    if user.totp_enabled:
        if not payload.totp_code or not verify_totp(decrypt_factor_secret(user.totp_secret_encrypted), payload.totp_code):
            if payload.totp_code:
                raise HTTPException(status_code=401, detail="Der Authenticator-Code ist ungültig.")
            return LoginChallengeResponse(challenge_token=create_factor_challenge(user_id=user.id, challenge=b"totp", purpose="totp-login"))
    return _issue_tokens(db, user)


@router.post("/login/2fa", response_model=TokenResponse)
def login_2fa(payload: Login2FARequest, db: Session = Depends(get_db)) -> TokenResponse:
    from ..security import decode_factor_challenge
    try:
        user_id, challenge = decode_factor_challenge(payload.challenge_token, purpose="totp-login")
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Die 2FA-Anmeldung ist abgelaufen.") from exc
    if challenge != b"totp":
        raise HTTPException(status_code=401, detail="Die 2FA-Anmeldung ist ungültig.")
    user = db.get(User, user_id)
    if user is None or not verify_totp(decrypt_factor_secret(user.totp_secret_encrypted), payload.code):
        raise HTTPException(status_code=401, detail="Der Authenticator-Code ist ungültig.")
    return _issue_tokens(db, user)


@router.post("/totp/setup", response_model=TotpSetupResponse)
def totp_setup(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TotpSetupResponse:
    secret = generate_totp_secret()
    current_user.totp_secret_encrypted = encrypt_factor_secret(secret)
    current_user.totp_enabled = False
    db.commit()
    return TotpSetupResponse(secret=secret, otpauth_uri=totp_uri(secret, current_user.email))


@router.post("/totp/enable", status_code=status.HTTP_204_NO_CONTENT)
def totp_enable(code: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    secret = decrypt_factor_secret(current_user.totp_secret_encrypted)
    if not verify_totp(secret, code):
        raise HTTPException(status_code=400, detail="Der Authenticator-Code ist ungültig.")
    current_user.totp_enabled = True
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/totp", status_code=status.HTTP_204_NO_CONTENT)
def totp_disable(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    current_user.totp_enabled = False
    current_user.totp_secret_encrypted = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/totp")
def totp_status(current_user: User = Depends(get_current_user)) -> dict[str, bool]:
    return {"enabled": current_user.totp_enabled}


@router.post("/passkeys/options")
def passkey_registration_options(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    return registration_options(request, current_user, db)


@router.post("/passkeys", status_code=status.HTTP_201_CREATED)
async def passkey_register(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    body = await request.json()
    credential = register_credential(request, current_user, body["credential"], str(body["challenge_token"]), str(body.get("name", "Passkey")), db)
    return {"id": credential.id, "name": credential.name}


@router.get("/passkeys")
def passkey_list(current_user: User = Depends(get_current_user)) -> list[dict[str, object]]:
    return [{"id": item.id, "name": item.name, "created_at": item.created_at.isoformat()} for item in current_user.passkeys]


@router.delete("/passkeys/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def passkey_delete(credential_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    credential = next((item for item in current_user.passkeys if item.id == credential_id), None)
    if credential is None:
        raise HTTPException(status_code=404, detail="Passkey nicht gefunden.")
    db.delete(credential)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/passkeys/login/options")
def passkey_login_options(email: str, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None:
        raise HTTPException(status_code=404, detail="Nutzerkonto nicht gefunden.")
    return authentication_options(request, user)


@router.post("/passkeys/login", response_model=TokenResponse)
async def passkey_login(request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    body = await request.json()
    user = authenticate_credential(request, body["credential"], str(body["challenge_token"]), db)
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(payload.refresh_token)))
    now = utcnow()
    if stored is None or stored.revoked_at is not None or _aware(stored.expires_at) <= now:
        raise HTTPException(status_code=401, detail="Der Refresh-Token ist ungültig oder abgelaufen.")
    user = db.get(User, stored.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Der Refresh-Token ist ungültig oder abgelaufen.")
    stored.revoked_at = now
    db.flush()
    return _issue_tokens(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(payload.refresh_token)))
    if stored and stored.revoked_at is None:
        stored.revoked_at = utcnow()
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren können Einladungen erstellen.")
    value = generate_opaque_token()
    invitation = Invitation(
        token_hash=token_hash(value),
        email=str(payload.email).lower() if payload.email else None,
        created_by_id=current_user.id,
        expires_at=utcnow() + timedelta(days=payload.expires_in_days),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse(id=invitation.id, token=value, email=invitation.email, expires_at=invitation.expires_at)


@router.post("/password-resets", response_model=PasswordResetCreated, status_code=status.HTTP_201_CREATED)
def create_password_reset(
    payload: PasswordResetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PasswordResetCreated:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren können Passwort-Resets erstellen.")
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        raise HTTPException(status_code=404, detail="Nutzerkonto nicht gefunden.")
    now = utcnow()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    value = generate_opaque_token()
    reset = PasswordResetToken(
        user_id=user.id,
        created_by_id=current_user.id,
        token_hash=token_hash(value),
        expires_at=now + timedelta(minutes=payload.expires_in_minutes),
    )
    db.add(reset)
    db.commit()
    db.refresh(reset)
    return PasswordResetCreated(token=value, email=user.email, expires_at=reset.expires_at)


@router.post("/password-reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> Response:
    reset = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_hash(payload.token))
        .with_for_update()
    )
    now = utcnow()
    if reset is None or reset.used_at is not None or _aware(reset.expires_at) <= now:
        raise HTTPException(status_code=400, detail="Der Reset-Token ist ungültig oder abgelaufen.")
    user = db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Der Reset-Token ist ungültig oder abgelaufen.")
    user.password_hash = hash_password(payload.new_password)
    reset.used_at = now
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    revoke_oauth_user_tokens(db, user.id, when=now)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
