from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


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
    training_goals: list[str] = Field(default_factory=list)
    avatar_data_url: str | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    hr_max: int | None = Field(default=None, ge=80, le=250)
    hr_rest: int | None = Field(default=None, ge=30, le=150)
    hr_zones: list[HeartRateZone] | None = Field(default=None, min_length=1, max_length=10)
    training_goals: list[str] | None = Field(default=None, max_length=12)

    @field_validator("training_goals")
    @classmethod
    def normalize_training_goals(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = list(dict.fromkeys(goal.strip() for goal in value if goal.strip()))
        if any(len(goal) > 80 for goal in normalized):
            raise ValueError("Ein Trainingsziel darf höchstens 80 Zeichen lang sein.")
        return normalized


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
    avg_speed_mps: float | None
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


class StatisticsSeriesPoint(BaseModel):
    period_start: date
    activity_count: int
    distance_m: float
    duration_s: float
    moving_time_s: float
    elevation_gain_m: float
    training_load: float
    avg_speed_mps: float | None
    avg_hr_bpm: float | None


class StatisticsComparison(BaseModel):
    date_from: date
    date_to: date
    activity_count: int
    distance_m: float
    duration_s: float
    moving_time_s: float
    elevation_gain_m: float
    training_load: float
    avg_speed_mps: float | None
    avg_hr_bpm: float | None
    changes: dict[str, float | None]


class StatisticsOverview(BaseModel):
    activity_count: int
    distance_m: float
    duration_s: float
    moving_time_s: float
    elevation_gain_m: float
    training_load: float
    avg_speed_mps: float
    avg_hr_bpm: float | None = None
    granularity: str = "month"
    series: list[StatisticsSeriesPoint] = Field(default_factory=list)
    comparison: StatisticsComparison | None = None
    by_month: list[dict[str, Any]]


class CompareRequest(BaseModel):
    activity_ids: list[str] = Field(min_length=2, max_length=10)


class ComparisonMetric(BaseModel):
    activity_id: str
    title: str
    distance_m: float
    duration_s: float
    moving_time_s: float
    elevation_gain_m: float
    avg_speed_mps: float | None
    avg_hr_bpm: float | None
    max_hr_bpm: int | None
    efficiency_kmh_per_bpm: float | None
    headwind_kmh: float | None
    relative_score: float | None


class ComparisonProfilePoint(BaseModel):
    progress_percent: float
    distance_km: float
    elevation_m: float | None
    speed_kmh: float | None
    heart_rate_bpm: int | None


class ComparisonProfile(BaseModel):
    activity_id: str
    title: str
    points: list[ComparisonProfilePoint]


class CompareResponse(BaseModel):
    activities: list[ActivityResponse]
    metrics: list[ComparisonMetric] = Field(default_factory=list)
    profiles: list[ComparisonProfile] = Field(default_factory=list)
    ai_summary: str | None = None
    ai_provider: str | None = None


class ChatHistoryMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)
    activity_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def limit_history_size(self) -> "ChatRequest":
        if sum(len(message.content) for message in self.history) > 32_000:
            raise ValueError("Der Chatverlauf ist für eine einzelne Anfrage zu lang.")
        return self


class ChatSource(BaseModel):
    activity_id: str
    title: str
    started_at: datetime


class ChatResponse(BaseModel):
    answer: str
    provider: str
    sources: list[ChatSource] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
