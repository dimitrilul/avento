from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Message(BaseModel):
    detail: str


class AccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)


class BootstrapRequest(AccountCreate):
    bootstrap_code: str | None = Field(default=None, min_length=1, max_length=512)


class RegisterRequest(AccountCreate):
    invite_token: str = Field(min_length=20, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class HeartRateZone(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    min_bpm: int = Field(ge=30, le=250)
    max_bpm: int = Field(ge=30, le=250)
    color: str = Field(default="#607D8B", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("max_bpm")
    @classmethod
    def max_not_empty(cls, value: int) -> int:
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    is_admin: bool
    hr_max: int
    hr_rest: int
    hr_zones: list[HeartRateZone]


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    hr_max: int | None = Field(default=None, ge=80, le=250)
    hr_rest: int | None = Field(default=None, ge=30, le=150)
    hr_zones: list[HeartRateZone] | None = Field(default=None, min_length=1, max_length=10)


class ProfilePasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=10, max_length=256)


class InvitationCreate(BaseModel):
    email: EmailStr | None = None
    expires_in_days: int = Field(default=7, ge=1, le=90)


class InvitationResponse(BaseModel):
    id: str
    token: str
    email: EmailStr | None
    expires_at: datetime


class PasswordResetCreate(BaseModel):
    email: EmailStr
    expires_in_minutes: int = Field(default=60, ge=5, le=1440)


class PasswordResetCreated(BaseModel):
    token: str
    email: EmailStr
    expires_at: datetime


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=10, max_length=256)


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=10000)


class ActivityResponse(BaseModel):
    id: str
    title: str
    type: str
    notes: str | None
    original_filename: str
    started_at: datetime
    ended_at: datetime
    distance_m: float
    duration_s: float
    moving_time_s: float
    pause_time_s: float
    avg_speed_mps: float
    max_speed_mps: float
    elevation_gain_m: float
    avg_hr_bpm: float | None
    max_hr_bpm: int | None
    avg_cadence_rpm: float | None
    max_cadence_rpm: int | None
    avg_power_w: float | None
    max_power_w: int | None
    training_load: float
    hr_zone_seconds: dict[str, float]
    weather: dict[str, Any] | None
    weather_status: str
    ai_summary: str | None
    ai_provider: str | None
    created_at: datetime
    updated_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    limit: int
    offset: int


class TrackPointResponse(BaseModel):
    time: datetime
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    distance_m: float | None = None
    heart_rate_bpm: int | None = None
    cadence_rpm: int | None = None
    power_w: int | None = None
    speed_mps: float | None = None


class TrackResponse(BaseModel):
    activity_id: str
    points: list[TrackPointResponse]


class WeatherResponse(BaseModel):
    status: str
    data: dict[str, Any] | None = None
    updated_at: datetime | None = None


class SummaryResponse(BaseModel):
    summary: str
    provider: str
    updated_at: datetime


class StatisticsOverview(BaseModel):
    activity_count: int
    distance_m: float
    duration_s: float
    moving_time_s: float
    elevation_gain_m: float
    training_load: float
    avg_speed_mps: float
    by_month: list[dict[str, Any]]


class CompareRequest(BaseModel):
    activity_ids: list[str] = Field(min_length=2, max_length=10)


class CompareResponse(BaseModel):
    activities: list[ActivityResponse]
