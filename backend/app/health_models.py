from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HealthConnection(Base):
    __tablename__ = "health_connections"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_health_connection_user"),
        UniqueConstraint("health_user_id_hash", name="uq_health_connection_external_user"),
        CheckConstraint(
            "status IN ('connected', 'reauthorization_required', 'revoked', 'error')",
            name="ck_health_connection_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    health_user_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    health_user_id_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    access_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    sources: Mapped[list["HealthDataSource"]] = relationship(cascade="all, delete-orphan")
    sync_runs: Mapped[list["HealthSyncRun"]] = relationship(cascade="all, delete-orphan")
    cursors: Mapped[list["HealthSyncCursor"]] = relationship(cascade="all, delete-orphan")
    metrics: Mapped[list["HealthMetric"]] = relationship(cascade="all, delete-orphan")
    sleeps: Mapped[list["HealthSleepSession"]] = relationship(cascade="all, delete-orphan")
    exercises: Mapped[list["HealthExercise"]] = relationship(cascade="all, delete-orphan")
    heart_rate_aggregates: Mapped[list["HealthHeartRateAggregate"]] = relationship(
        cascade="all, delete-orphan"
    )
    zones: Mapped[list["HealthHeartRateZone"]] = relationship(cascade="all, delete-orphan")
    gaps: Mapped[list["HealthDataGap"]] = relationship(cascade="all, delete-orphan")


class HealthOAuthState(Base):
    __tablename__ = "health_oauth_states"
    __table_args__ = (UniqueConstraint("state_hash", name="uq_health_oauth_state_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), index=True)
    pkce_verifier_encrypted: Mapped[str] = mapped_column(Text)
    redirect_uri: Mapped[str] = mapped_column(String(2048))
    requested_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthDataSource(Base):
    __tablename__ = "health_data_sources"
    __table_args__ = (
        UniqueConstraint("connection_id", "fingerprint", name="uq_health_source_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    recording_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(40), nullable=True)
    device_manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    device_form_factor: Mapped[str | None] = mapped_column(String(60), nullable=True)
    application_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthSyncRun(Base):
    __tablename__ = "health_sync_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'partial', 'failed')",
            name="ck_health_sync_run_status",
        ),
        CheckConstraint("fetched_count >= 0 AND stored_count >= 0 AND rejected_count >= 0", name="ck_health_sync_counts"),
        Index("ix_health_sync_run_user_started", "user_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(20), default="manual")
    status: Mapped[str] = mapped_column(String(20), default="running")
    range_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    range_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    stored_count: Mapped[int] = mapped_column(Integer, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HealthSyncCursor(Base):
    __tablename__ = "health_sync_cursors"
    __table_args__ = (
        UniqueConstraint("connection_id", "data_type", name="uq_health_sync_cursor_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    data_type: Mapped[str] = mapped_column(String(80))
    completed_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)


class HealthMetric(Base):
    __tablename__ = "health_metrics"
    __table_args__ = (
        UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_metric_dedupe"),
        CheckConstraint("value = value", name="ck_health_metric_finite"),
        Index("ix_health_metric_user_date_type", "user_id", "local_date", "metric_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    data_type: Mapped[str] = mapped_column(String(80))
    metric_type: Mapped[str] = mapped_column(String(100))
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    local_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    utc_offset_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_family: Mapped[str] = mapped_column(String(40), default="all-sources")
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthSleepSession(Base):
    __tablename__ = "health_sleep_sessions"
    __table_args__ = (
        UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_sleep_dedupe"),
        CheckConstraint("end_at > start_at", name="ck_health_sleep_interval"),
        Index("ix_health_sleep_user_end", "user_id", "end_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True
    )
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    end_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    local_date: Mapped[date] = mapped_column(Date)
    sleep_type: Mapped[str] = mapped_column(String(30))
    is_nap: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    stages_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    minutes_asleep: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_awake: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_to_fall_asleep: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overlaps_other_session: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    stages: Mapped[list["HealthSleepStage"]] = relationship(cascade="all, delete-orphan")


class HealthSleepStage(Base):
    __tablename__ = "health_sleep_stages"
    __table_args__ = (
        UniqueConstraint("session_id", "start_at", "end_at", "stage_type", name="uq_health_sleep_stage"),
        CheckConstraint("end_at > start_at", name="ck_health_sleep_stage_interval"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("health_sleep_sessions.id", ondelete="CASCADE"), index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    end_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    stage_type: Mapped[str] = mapped_column(String(30))


class HealthExercise(Base):
    __tablename__ = "health_exercises"
    __table_args__ = (
        UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_exercise_dedupe"),
        CheckConstraint("end_at > start_at", name="ck_health_exercise_interval"),
        Index("ix_health_exercise_user_start", "user_id", "start_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("health_data_sources.id", ondelete="SET NULL"), nullable=True
    )
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    end_utc_offset_seconds: Mapped[int] = mapped_column(Integer, default=0)
    local_date: Mapped[date] = mapped_column(Date)
    exercise_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_zone_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate_zone_seconds: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    has_gps: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthHeartRateAggregate(Base):
    __tablename__ = "health_heart_rate_aggregates"
    __table_args__ = (
        UniqueConstraint("connection_id", "dedupe_hash", name="uq_health_hr_aggregate_dedupe"),
        CheckConstraint("end_at > start_at", name="ck_health_hr_aggregate_interval"),
        CheckConstraint("min_bpm >= 20 AND max_bpm <= 300 AND min_bpm <= avg_bpm AND avg_bpm <= max_bpm", name="ck_health_hr_aggregate_values"),
        Index("ix_health_hr_user_grain_start", "user_id", "granularity", "start_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    granularity: Mapped[str] = mapped_column(String(20))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    local_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_bpm: Mapped[float] = mapped_column(Float)
    avg_bpm: Mapped[float] = mapped_column(Float)
    max_bpm: Mapped[float] = mapped_column(Float)
    sleep_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("health_sleep_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    exercise_id: Mapped[str | None] = mapped_column(
        ForeignKey("health_exercises.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_family: Mapped[str] = mapped_column(String(40), default="all-sources")
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthHeartRateZone(Base):
    __tablename__ = "health_heart_rate_zones"
    __table_args__ = (
        UniqueConstraint("connection_id", "local_date", "zone_type", name="uq_health_hr_zone_day"),
        CheckConstraint("min_bpm >= 20 AND max_bpm <= 300 AND min_bpm <= max_bpm", name="ck_health_hr_zone_values"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    zone_type: Mapped[str] = mapped_column(String(30))
    min_bpm: Mapped[int] = mapped_column(Integer)
    max_bpm: Mapped[int] = mapped_column(Integer)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthDataGap(Base):
    __tablename__ = "health_data_gaps"
    __table_args__ = (
        UniqueConstraint("connection_id", "data_type", "local_date", name="uq_health_gap_day"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("health_connections.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    data_type: Mapped[str] = mapped_column(String(80))
    local_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(String(40), default="missing")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
