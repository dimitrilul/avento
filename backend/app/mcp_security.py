from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from .config import get_settings
from .mcp_models import MCP_SCOPES, McpAccessToken, McpAuditLog, McpClient
from .models import User


MCP_TOKEN_TTL_DEFAULT_MINUTES = 10
MCP_TOKEN_TTL_HARD_MAX_MINUTES = 15
MAX_MCP_BODY_BYTES = 64 * 1024
MAX_TOKEN_BODY_BYTES = 4 * 1024
MAX_TOOL_ARGUMENT_BYTES = 16 * 1024
MAX_TOOL_RESULT_BYTES = 48 * 1024

_DEFAULT_ALLOWED_ORIGINS = "http://localhost,http://127.0.0.1,http://[::1]"
_secret_hasher = PasswordHasher()
_dummy_secret_hash = _secret_hasher.hash("avento-mcp-dummy-secret-for-constant-work")

_AUDIT_METHODS = {
    "initialize",
    "notifications/initialized",
    "notifications/cancelled",
    "ping",
    "tools/list",
    "tools/call",
    "http/get",
    "http/delete",
}
_AUDIT_TOOLS = {
    "list_activities",
    "get_activity_details",
    "get_statistics",
    "get_records_and_insights",
}
_AUDIT_OUTCOMES = {"success", "accepted", "rejected", "failed"}
_AUDIT_ERRORS = {
    "missing_token",
    "invalid_token",
    "expired_token",
    "revoked_token",
    "inactive_client",
    "invalid_origin",
    "invalid_transport",
    "payload_too_large",
    "invalid_request",
    "unsupported_version",
    "unknown_method",
    "tool_unavailable",
    "invalid_arguments",
    "tool_failed",
    "result_too_large",
    "internal_error",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def generate_client_id() -> str:
    return f"avmcp_{secrets.token_urlsafe(18)}"


def generate_client_secret() -> str:
    return f"avmcp_secret_{secrets.token_urlsafe(48)}"


def hash_client_secret(secret: str) -> str:
    return _secret_hasher.hash(secret)


def verify_client_secret(secret: str, secret_hash: str) -> bool:
    try:
        return _secret_hasher.verify(secret_hash, secret)
    except (VerificationError, InvalidHashError):
        return False


def hash_access_token(token: str) -> str:
    return hashlib.sha256(b"avento-mcp-access\0" + token.encode("utf-8")).hexdigest()


def mcp_token_ttl_seconds() -> int:
    configured = getattr(get_settings(), "mcp_access_token_minutes", MCP_TOKEN_TTL_DEFAULT_MINUTES)
    try:
        minutes = int(configured)
    except (TypeError, ValueError):
        minutes = MCP_TOKEN_TTL_DEFAULT_MINUTES
    minutes = max(1, min(minutes, MCP_TOKEN_TTL_HARD_MAX_MINUTES))
    return minutes * 60


def _normalized_origin(value: str) -> tuple[str, str, int | None] | None:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    return parsed.scheme.lower(), parsed.hostname.lower(), port


def mcp_origin_allowed(origin: str | None) -> bool:
    # Non-browser MCP clients normally omit Origin. Any supplied value is checked.
    if origin is None:
        return True
    candidate = _normalized_origin(origin.strip())
    if candidate is None:
        return False
    configured = str(getattr(get_settings(), "mcp_allowed_origins", _DEFAULT_ALLOWED_ORIGINS))
    for raw_allowed in configured.split(","):
        allowed = _normalized_origin(raw_allowed.strip())
        if allowed is None:
            continue
        same_host = candidate[:2] == allowed[:2]
        same_port = allowed[2] is None or candidate[2] == allowed[2]
        if same_host and same_port:
            return True
    return False


@dataclass(frozen=True)
class McpPrincipal:
    client_pk: str
    client_id: str
    owner_user_id: str
    token_pk: str
    scopes: tuple[str, ...]


class McpAuthenticationError(Exception):
    def __init__(self, reason: str, principal: McpPrincipal | None = None):
        super().__init__("MCP authentication failed")
        self.reason = reason if reason in _AUDIT_ERRORS else "invalid_token"
        self.principal = principal


class McpCredentialError(Exception):
    pass


def _principal_for(token: McpAccessToken, client: McpClient) -> McpPrincipal:
    client_scopes = {scope for scope in (client.scopes or []) if scope in MCP_SCOPES}
    token_scopes = {scope for scope in (token.scopes or []) if scope in MCP_SCOPES}
    effective = tuple(scope for scope in MCP_SCOPES if scope in client_scopes & token_scopes)
    return McpPrincipal(
        client_pk=client.id,
        client_id=client.client_id,
        owner_user_id=client.owner_user_id,
        token_pk=token.id,
        scopes=effective,
    )


def authenticate_mcp_bearer(
    db: Session,
    authorization: str | None,
    *,
    touch: bool = True,
) -> McpPrincipal:
    if not authorization or len(authorization) > 768:
        raise McpAuthenticationError("missing_token" if not authorization else "invalid_token")
    scheme, separator, raw_token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not raw_token or " " in raw_token:
        raise McpAuthenticationError("invalid_token")
    if not raw_token.startswith("avmcp_at_") or not 32 <= len(raw_token) <= 512:
        raise McpAuthenticationError("invalid_token")

    token = db.scalar(
        select(McpAccessToken)
        .options(joinedload(McpAccessToken.client))
        .where(McpAccessToken.token_hash == hash_access_token(raw_token))
    )
    if token is None or token.client is None:
        raise McpAuthenticationError("invalid_token")
    client = token.client
    principal = _principal_for(token, client)
    now = utcnow()
    if token.revoked_at is not None:
        raise McpAuthenticationError("revoked_token", principal)
    if aware_utc(token.expires_at) <= now:
        raise McpAuthenticationError("expired_token", principal)
    if not client.is_active or client.revoked_at is not None:
        raise McpAuthenticationError("inactive_client", principal)
    if db.scalar(select(User.id).where(User.id == client.owner_user_id)) is None:
        raise McpAuthenticationError("inactive_client", principal)
    if touch:
        token.last_used_at = now
        client.last_used_at = now
    return principal


def issue_mcp_access_token(
    db: Session,
    client_id: str,
    client_secret: str,
    requested_scopes: list[str] | None,
) -> tuple[str, int, list[str]]:
    client = db.scalar(
        select(McpClient).where(McpClient.client_id == client_id).with_for_update()
    )
    secret_hash = client.secret_hash if client is not None else _dummy_secret_hash
    secret_valid = verify_client_secret(client_secret, secret_hash)
    if client is None or not secret_valid:
        raise McpCredentialError
    if not client.is_active or client.revoked_at is not None:
        raise McpCredentialError
    if db.scalar(select(User.id).where(User.id == client.owner_user_id)) is None:
        raise McpCredentialError

    assigned = [scope for scope in MCP_SCOPES if scope in set(client.scopes or [])]
    scopes = assigned if requested_scopes is None else list(requested_scopes)
    if not set(scopes).issubset(set(assigned)):
        raise McpCredentialError

    expires_in = mcp_token_ttl_seconds()
    raw_token = f"avmcp_at_{secrets.token_urlsafe(48)}"
    db.add(
        McpAccessToken(
            client_pk=client.id,
            token_hash=hash_access_token(raw_token),
            scopes=scopes,
            expires_at=utcnow() + timedelta(seconds=expires_in),
        )
    )
    db.commit()
    return raw_token, expires_in, scopes


def revoke_client_tokens(db: Session, client_pk: str, *, when: datetime | None = None) -> None:
    revoked_at = when or utcnow()
    db.execute(
        update(McpAccessToken)
        .where(McpAccessToken.client_pk == client_pk, McpAccessToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


def _request_id_hash(request_id: object) -> str | None:
    if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
        return None
    encoded = json.dumps(request_id, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b"avento-mcp-request-id\0" + encoded).hexdigest()


def audit_mcp_request(
    db: Session,
    *,
    principal: McpPrincipal | None,
    request_id: object = None,
    method: object = None,
    tool_name: object = None,
    outcome: str,
    error_type: str | None,
    jsonrpc_error_code: int | None,
    http_status: int,
    duration_ms: int,
) -> None:
    safe_method = method if isinstance(method, str) and method in _AUDIT_METHODS else "unknown"
    safe_tool = tool_name if isinstance(tool_name, str) and tool_name in _AUDIT_TOOLS else None
    safe_outcome = outcome if outcome in _AUDIT_OUTCOMES else "failed"
    safe_error = error_type if error_type in _AUDIT_ERRORS else ("internal_error" if error_type else None)
    entry = McpAuditLog(
        client_pk=principal.client_pk if principal else None,
        owner_user_id=principal.owner_user_id if principal else None,
        request_id_hash=_request_id_hash(request_id),
        method=safe_method,
        tool_name=safe_tool,
        outcome=safe_outcome,
        error_type=safe_error,
        jsonrpc_error_code=jsonrpc_error_code,
        http_status=max(100, min(int(http_status), 599)),
        duration_ms=max(0, min(int(duration_ms), 2_147_483_647)),
    )
    try:
        db.add(entry)
        db.commit()
    except SQLAlchemyError:
        # Auditing must never expose a database error or replace the protocol response.
        db.rollback()
