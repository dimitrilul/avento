from __future__ import annotations

import base64
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import PasskeyCredential, User
from .security import create_factor_challenge, decode_factor_challenge


def _origin(request: Request) -> str:
    settings = get_settings()
    return (settings.public_url or str(request.base_url)).rstrip("/")


def _rp_id(request: Request) -> str:
    settings = get_settings()
    return settings.webauthn_rp_id or (urlsplit(_origin(request)).hostname or "localhost")


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def registration_options(request: Request, user: User, db: Session) -> dict[str, object]:
    credentials = [
        PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c.credential_id + "=" * (-len(c.credential_id) % 4)))
        for c in user.passkeys
    ]
    options = generate_registration_options(
        rp_id=_rp_id(request), rp_name=get_settings().webauthn_rp_name,
        user_id=user.id.encode(), user_name=user.email, user_display_name=user.display_name,
        exclude_credentials=credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    return {"options": __import__("json").loads(options_to_json(options)),
            "challenge_token": create_factor_challenge(user_id=user.id, challenge=options.challenge, purpose="passkey-register")}


def register_credential(request: Request, user: User, payload: dict[str, object], challenge_token: str, name: str, db: Session) -> PasskeyCredential:
    subject, challenge = decode_factor_challenge(challenge_token, purpose="passkey-register")
    if subject != user.id:
        raise HTTPException(status_code=400, detail="Die Passkey-Challenge ist ungültig.")
    try:
        verified = verify_registration_response(
            credential=payload, expected_challenge=challenge, expected_rp_id=_rp_id(request), expected_origin=_origin(request)
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Der Passkey konnte nicht bestätigt werden.") from exc
    credential = PasskeyCredential(
        user_id=user.id, credential_id=_b64(verified.credential_id), public_key=verified.credential_public_key,
        sign_count=verified.sign_count, name=name.strip() or "Passkey",
    )
    db.add(credential)
    db.commit()
    return credential


def authentication_options(request: Request, user: User) -> dict[str, object]:
    if not user.passkeys:
        raise HTTPException(status_code=400, detail="Für dieses Konto ist noch kein Passkey eingerichtet.")
    options = generate_authentication_options(
        rp_id=_rp_id(request),
        allow_credentials=[PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c.credential_id + "=" * (-len(c.credential_id) % 4))) for c in user.passkeys],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return {"options": __import__("json").loads(options_to_json(options)),
            "challenge_token": create_factor_challenge(user_id=user.id, challenge=options.challenge, purpose="passkey-login")}


def authenticate_credential(request: Request, payload: dict[str, object], challenge_token: str, db: Session) -> User:
    user_id, challenge = decode_factor_challenge(challenge_token, purpose="passkey-login")
    credential_id = str(payload.get("rawId") or payload.get("id") or "")
    credential = db.scalar(select(PasskeyCredential).where(PasskeyCredential.credential_id == credential_id))
    user = db.get(User, user_id)
    if credential is None or user is None or credential.user_id != user.id:
        raise HTTPException(status_code=401, detail="Der Passkey ist ungültig.")
    try:
        verified = verify_authentication_response(
            credential=payload, expected_challenge=challenge, expected_rp_id=_rp_id(request), expected_origin=_origin(request),
            credential_public_key=credential.public_key, credential_current_sign_count=credential.sign_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Der Passkey konnte nicht bestätigt werden.") from exc
    credential.sign_count = verified.new_sign_count
    from .models import utcnow
    credential.last_used_at = utcnow()
    db.commit()
    return user
