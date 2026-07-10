from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


MCP_SCOPES = (
    "activities:read",
    "activities:detail",
    "statistics:read",
    "insights:read",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid4_str() -> str:
    return str(uuid.uuid4())


class McpClient(Base):
    __tablename__ = "mcp_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    client_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    secret_hash: Mapped[str] = mapped_column(String(512))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    access_tokens: Mapped[list["McpAccessToken"]] = relationship(
        back_populates="client", cascade="all, delete-orphan", passive_deletes=True
    )
    audit_logs: Mapped[list["McpAuditLog"]] = relationship(
        back_populates="client", passive_deletes=True
    )


class McpAccessToken(Base):
    __tablename__ = "mcp_access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    client_pk: Mapped[str] = mapped_column(
        ForeignKey("mcp_clients.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    client: Mapped[McpClient] = relationship(back_populates="access_tokens")


class McpOAuthClient(Base):
    __tablename__ = "mcp_oauth_clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    client_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    client_name: Mapped[str] = mapped_column(String(120))
    redirect_uris: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class McpOAuthAuthorizationCode(Base):
    __tablename__ = "mcp_oauth_authorization_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_pk: Mapped[str] = mapped_column(
        ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    redirect_uri: Mapped[str] = mapped_column(String(2048))
    code_challenge: Mapped[str] = mapped_column(String(128))
    code_challenge_method: Mapped[str] = mapped_column(String(16))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    resource: Mapped[str] = mapped_column(String(2048))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class McpOAuthAccessToken(Base):
    __tablename__ = "mcp_oauth_access_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_pk: Mapped[str] = mapped_column(
        ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    resource: Mapped[str] = mapped_column(String(2048))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class McpOAuthRefreshToken(Base):
    __tablename__ = "mcp_oauth_refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_pk: Mapped[str] = mapped_column(
        ForeignKey("mcp_oauth_clients.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    resource: Mapped[str] = mapped_column(String(2048))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class McpAuditLog(Base):
    __tablename__ = "mcp_audit_logs"
    __table_args__ = (
        Index("ix_mcp_audit_logs_created_at", "created_at"),
        Index("ix_mcp_audit_logs_client_created", "client_pk", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid4_str)
    client_pk: Mapped[str | None] = mapped_column(
        ForeignKey("mcp_clients.id", ondelete="SET NULL"), nullable=True
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_id_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(80))
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24))
    error_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    jsonrpc_error_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    client: Mapped[McpClient | None] = relationship(back_populates="audit_logs")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _canonical_scopes(scopes: list[str]) -> list[str]:
    if len(scopes) != len(set(scopes)):
        raise ValueError("Scopes dürfen nicht doppelt vorkommen.")
    unknown = set(scopes) - set(MCP_SCOPES)
    if unknown:
        raise ValueError("Mindestens ein Scope ist unbekannt.")
    selected = set(scopes)
    return [scope for scope in MCP_SCOPES if scope in selected]


class McpClientCreate(_StrictModel):
    owner_user_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list, max_length=len(MCP_SCOPES))

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Der Name darf nicht leer sein.")
        return normalized

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        return _canonical_scopes(value)


class McpClientUpdate(_StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    scopes: list[str] | None = Field(default=None, max_length=len(MCP_SCOPES))
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Der Name darf nicht leer sein.")
        return normalized

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _canonical_scopes(value)

    @model_validator(mode="after")
    def require_change(self) -> "McpClientUpdate":
        if not self.model_fields_set:
            raise ValueError("Mindestens eine Änderung ist erforderlich.")
        return self


class McpClientResponse(_StrictModel):
    client_id: str
    owner_user_id: str
    name: str
    scopes: list[str]
    is_active: bool
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class McpClientCreated(McpClientResponse):
    client_secret: str


class McpSecretRotated(_StrictModel):
    client_id: str
    client_secret: str


class McpAccessTokenRequest(_StrictModel):
    client_id: str = Field(min_length=12, max_length=80, pattern=r"^avmcp_[A-Za-z0-9_-]+$")
    client_secret: str = Field(
        min_length=24,
        max_length=512,
        pattern=r"^avmcp_secret_[A-Za-z0-9_-]+$",
    )
    scopes: list[str] | None = Field(default=None, max_length=len(MCP_SCOPES))

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _canonical_scopes(value)


class McpAccessTokenResponse(_StrictModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scopes: list[str]


class McpAuditResponse(_StrictModel):
    client_id: str | None
    method: str
    tool_name: str | None
    outcome: str
    error_type: str | None
    jsonrpc_error_code: int | None
    http_status: int
    duration_ms: int
    created_at: datetime
