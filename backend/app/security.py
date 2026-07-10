from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .config import get_settings


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), expires_in


def decode_access_token(token: str) -> str:
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise jwt.InvalidTokenError("Not an access token")
    return str(payload["sub"])


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

