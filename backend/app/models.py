from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid4_str() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(120))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    hr_max: Mapped[int] = mapped_column(Integer, default=190)
    hr_rest: Mapped[int] = mapped_column(Integer, default=60)
    hr_zones: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    activities: Mapped[list["Activity"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (UniqueConstraint("user_id", "file_hash", name="uq_activity_user_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    original_file_path: Mapped[str] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(String(200))
    activity_type: Mapped[str] = mapped_column(String(50), default="cycling")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    distance_m: Mapped[float] = mapped_column(Float, default=0)
    duration_s: Mapped[float] = mapped_column(Float, default=0)
    moving_time_s: Mapped[float] = mapped_column(Float, default=0)
    pause_time_s: Mapped[float] = mapped_column(Float, default=0)
    avg_speed_mps: Mapped[float] = mapped_column(Float, default=0)
    max_speed_mps: Mapped[float] = mapped_column(Float, default=0)
    elevation_gain_m: Mapped[float] = mapped_column(Float, default=0)
    avg_hr_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hr_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_cadence_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_cadence_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_power_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_load: Mapped[float] = mapped_column(Float, default=0)
    hr_zone_seconds: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    track_points: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    weather: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    weather_status: Mapped[str] = mapped_column(String(30), default="pending")
    weather_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ai_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="activities")
