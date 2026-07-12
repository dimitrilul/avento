from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HealthOAuthStartResponse(BaseModel):
    authorization_url: str
    expires_at: datetime
    mock_mode: bool = False


class HealthDataSourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: str | None = None
    recording_method: str | None = None
    device_manufacturer: str | None = None
    device_name: str | None = None
    application_name: str | None = None
    last_seen_at: datetime


class HealthConnectionStatus(BaseModel):
    provider: Literal["google_health_api_v4"] = "google_health_api_v4"
    enabled: bool = False
    mock_mode: bool = False
    connected: bool
    status: str
    granted_scopes: list[str] = Field(default_factory=list)
    missing_scopes: list[str] = Field(default_factory=list)
    last_sync_at: datetime | None = None
    last_error_code: str | None = None
    data_sources: list[HealthDataSourceSummary] = Field(default_factory=list)


class HealthSyncRequest(BaseModel):
    lookback_days: int | None = Field(default=None, ge=1, le=365)


class HealthSyncResponse(BaseModel):
    run_id: str
    status: str
    range_start: datetime
    range_end: datetime
    fetched_count: int
    stored_count: int
    rejected_count: int
    error_code: str | None = None


class HealthMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_type: str
    value: float
    unit: str
    observed_at: datetime | None
    start_at: datetime | None
    end_at: datetime | None
    local_date: date | None
    imported_at: datetime


class HealthHeartRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    granularity: str
    start_at: datetime
    end_at: datetime
    local_date: date | None
    min_bpm: float
    avg_bpm: float
    max_bpm: float
    sleep_session_id: str | None
    exercise_id: str | None


class HealthSleepStageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_at: datetime
    end_at: datetime
    stage_type: str


class HealthSleepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    start_at: datetime
    end_at: datetime
    local_date: date
    sleep_type: str
    is_nap: bool
    minutes_asleep: int | None
    minutes_awake: int | None
    overlaps_other_session: bool
    stages: list[HealthSleepStageResponse] = Field(default_factory=list)


class HealthExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    start_at: datetime
    end_at: datetime
    local_date: date
    exercise_type: str
    title: str | None
    active_duration_seconds: float | None
    calories_kcal: float | None
    distance_m: float | None
    steps: int | None
    average_heart_rate_bpm: int | None
    active_zone_minutes: int | None
    heart_rate_zone_seconds: dict[str, float]


class HealthDataResponse(BaseModel):
    metrics: list[HealthMetricResponse] = Field(default_factory=list)
    heart_rate: list[HealthHeartRateResponse] = Field(default_factory=list)
    sleeps: list[HealthSleepResponse] = Field(default_factory=list)
    exercises: list[HealthExerciseResponse] = Field(default_factory=list)


class HealthOverviewResponse(BaseModel):
    date: date
    generated_at: datetime
    scores: dict[str, Any] = Field(default_factory=dict)
    factors: list[dict[str, Any]] = Field(default_factory=list)
    coverage: dict[str, float] = Field(default_factory=dict)
    baselines: dict[str, Any] = Field(default_factory=dict)
    uncertainty: list[str] = Field(default_factory=list)


class _ExternalModel(BaseModel):
    # Google can add fields without breaking ingestion. Only explicitly modeled
    # fields survive model_dump(), which makes normalization whitelist-based.
    model_config = ConfigDict(extra="ignore")


class GoogleDate(_ExternalModel):
    year: int = Field(ge=2000, le=2200)
    month: int = Field(ge=1, le=12)
    day: int = Field(ge=1, le=31)

    def as_date(self) -> date:
        return date(self.year, self.month, self.day)


class GoogleCivilTime(_ExternalModel):
    date: GoogleDate
    time: dict[str, int] = Field(default_factory=dict)


class GoogleInterval(_ExternalModel):
    startTime: datetime
    endTime: datetime
    startUtcOffset: str = "0s"
    endUtcOffset: str = "0s"
    civilStartTime: GoogleCivilTime | None = None
    civilEndTime: GoogleCivilTime | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> "GoogleInterval":
        if self.startTime.tzinfo is None or self.endTime.tzinfo is None:
            raise ValueError("Zeitintervalle benötigen eine Zeitzone.")
        if self.endTime <= self.startTime:
            raise ValueError("Das Ende muss nach dem Start liegen.")
        return self


class GoogleDataSource(_ExternalModel):
    recordingMethod: str | None = Field(default=None, max_length=80)
    platform: str | None = Field(default=None, max_length=80)
    device: dict[str, Any] | None = None
    application: dict[str, Any] | None = None


class GoogleSleepStage(_ExternalModel):
    startTime: datetime
    endTime: datetime
    startUtcOffset: str = "0s"
    endUtcOffset: str = "0s"
    type: str = Field(max_length=40)

    @model_validator(mode="after")
    def valid_stage(self) -> "GoogleSleepStage":
        if self.startTime.tzinfo is None or self.endTime.tzinfo is None or self.endTime <= self.startTime:
            raise ValueError("Ungültiges Schlafphasenintervall.")
        return self


class GoogleSleepMetadata(_ExternalModel):
    stagesStatus: str | None = Field(default=None, max_length=80)
    processed: bool = False
    nap: bool = False
    manuallyEdited: bool = False


class GoogleSleepSummary(_ExternalModel):
    minutesInSleepPeriod: int | None = Field(default=None, ge=0, le=2880)
    minutesAfterWakeUp: int | None = Field(default=None, ge=0, le=1440)
    minutesToFallAsleep: int | None = Field(default=None, ge=0, le=1440)
    minutesAsleep: int | None = Field(default=None, ge=0, le=2880)
    minutesAwake: int | None = Field(default=None, ge=0, le=2880)


class GoogleSleep(_ExternalModel):
    interval: GoogleInterval
    type: str = Field(default="SLEEP_TYPE_UNSPECIFIED", max_length=40)
    stages: list[GoogleSleepStage] = Field(default_factory=list, max_length=3000)
    metadata: GoogleSleepMetadata = Field(default_factory=GoogleSleepMetadata)
    summary: GoogleSleepSummary = Field(default_factory=GoogleSleepSummary)
    updateTime: datetime | None = None

    @model_validator(mode="after")
    def stages_within_session(self) -> "GoogleSleep":
        previous_end: datetime | None = None
        for stage in sorted(self.stages, key=lambda item: item.startTime):
            if stage.startTime < self.interval.startTime or stage.endTime > self.interval.endTime:
                raise ValueError("Schlafphase liegt außerhalb der Schlafsitzung.")
            if previous_end is not None and stage.startTime < previous_end:
                raise ValueError("Schlafphasen dürfen sich nicht überschneiden.")
            previous_end = stage.endTime
        return self


class GoogleExerciseMetrics(_ExternalModel):
    caloriesKcal: float | None = Field(default=None, ge=0, le=100000)
    distanceMillimeters: float | None = Field(default=None, ge=0, le=10_000_000_000)
    steps: int | None = Field(default=None, ge=0, le=10_000_000)
    averageHeartRateBeatsPerMinute: int | None = Field(default=None, ge=20, le=300)
    activeZoneMinutes: int | None = Field(default=None, ge=0, le=100000)
    heartRateZoneDurations: dict[str, str] = Field(default_factory=dict)


class GoogleExerciseMetadata(_ExternalModel):
    hasGps: bool = False


class GoogleExercise(_ExternalModel):
    interval: GoogleInterval
    exerciseType: str = Field(max_length=100)
    metricsSummary: GoogleExerciseMetrics
    exerciseMetadata: GoogleExerciseMetadata = Field(default_factory=GoogleExerciseMetadata)
    displayName: str | None = Field(default=None, max_length=200)
    activeDuration: str | None = Field(default=None, max_length=40)
    updateTime: datetime | None = None


class GoogleDailyRestingHeartRate(_ExternalModel):
    date: GoogleDate
    beatsPerMinute: int = Field(ge=20, le=300)


class GoogleDailyHeartRateVariability(_ExternalModel):
    date: GoogleDate
    averageHeartRateVariabilityMilliseconds: float | None = Field(default=None, ge=0, le=5000)
    nonRemHeartRateBeatsPerMinute: int | None = Field(default=None, ge=20, le=300)
    entropy: float | None = Field(default=None, ge=0, le=100)
    deepSleepRootMeanSquareOfSuccessiveDifferencesMilliseconds: float | None = Field(
        default=None, ge=0, le=5000
    )


class GoogleDailyRespiratoryRate(_ExternalModel):
    date: GoogleDate
    breathsPerMinute: float = Field(ge=1, le=100)


class GoogleRespiratorySleepStats(_ExternalModel):
    breathsPerMinute: float = Field(ge=1, le=100)
    standardDeviation: float | None = Field(default=None, ge=0, le=100)
    signalToNoise: float | None = Field(default=None, ge=0, le=10000)


class GoogleRespiratorySleepSummary(_ExternalModel):
    sampleTime: dict[str, Any]
    fullSleepStats: GoogleRespiratorySleepStats
    deepSleepStats: GoogleRespiratorySleepStats | None = None
    lightSleepStats: GoogleRespiratorySleepStats | None = None
    remSleepStats: GoogleRespiratorySleepStats | None = None


class GoogleDailyOxygenSaturation(_ExternalModel):
    date: GoogleDate
    averagePercentage: float = Field(ge=0, le=100)
    lowerBoundPercentage: float = Field(ge=0, le=100)
    upperBoundPercentage: float = Field(ge=0, le=100)
    standardDeviationPercentage: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def ordered_bounds(self) -> "GoogleDailyOxygenSaturation":
        if not self.lowerBoundPercentage <= self.averagePercentage <= self.upperBoundPercentage:
            raise ValueError("SpO₂-Grenzen sind inkonsistent.")
        return self


class GoogleHeartRateZone(_ExternalModel):
    heartRateZoneType: str = Field(max_length=40)
    minBeatsPerMinute: int = Field(ge=20, le=300)
    maxBeatsPerMinute: int = Field(ge=20, le=300)

    @model_validator(mode="after")
    def ordered_bounds(self) -> "GoogleHeartRateZone":
        if self.minBeatsPerMinute > self.maxBeatsPerMinute:
            raise ValueError("Herzfrequenzzone ist ungültig.")
        return self


class GoogleDailyHeartRateZones(_ExternalModel):
    date: GoogleDate
    heartRateZones: list[GoogleHeartRateZone] = Field(max_length=20)


class GoogleRollupHeartRate(_ExternalModel):
    beatsPerMinuteAvg: float = Field(ge=20, le=300)
    beatsPerMinuteMax: float = Field(ge=20, le=300)
    beatsPerMinuteMin: float = Field(ge=20, le=300)

    @model_validator(mode="after")
    def ordered_values(self) -> "GoogleRollupHeartRate":
        values = (self.beatsPerMinuteMin, self.beatsPerMinuteAvg, self.beatsPerMinuteMax)
        if not all(isfinite(value) for value in values) or not values[0] <= values[1] <= values[2]:
            raise ValueError("Herzfrequenz-Rollup ist inkonsistent.")
        return self


class GooglePhysicalRollupPoint(_ExternalModel):
    startTime: datetime
    endTime: datetime
    heartRate: GoogleRollupHeartRate | None = None


class GoogleDailyRollupPoint(_ExternalModel):
    civilStartTime: GoogleCivilTime
    civilEndTime: GoogleCivilTime
    steps: dict[str, Any] | None = None
    activeEnergyBurned: dict[str, Any] | None = None
    totalCalories: dict[str, Any] | None = None
    heartRate: GoogleRollupHeartRate | None = None


SUPPORTED_DATA_MODELS: dict[str, tuple[str, type[_ExternalModel]]] = {
    "sleep": ("sleep", GoogleSleep),
    "exercise": ("exercise", GoogleExercise),
    "daily-resting-heart-rate": ("dailyRestingHeartRate", GoogleDailyRestingHeartRate),
    "daily-heart-rate-variability": ("dailyHeartRateVariability", GoogleDailyHeartRateVariability),
    "daily-respiratory-rate": ("dailyRespiratoryRate", GoogleDailyRespiratoryRate),
    "respiratory-rate-sleep-summary": ("respiratoryRateSleepSummary", GoogleRespiratorySleepSummary),
    "daily-oxygen-saturation": ("dailyOxygenSaturation", GoogleDailyOxygenSaturation),
    "daily-heart-rate-zones": ("dailyHeartRateZones", GoogleDailyHeartRateZones),
}


def validate_google_data_point(
    payload: dict[str, Any], data_type: str
) -> tuple[_ExternalModel, GoogleDataSource | None, str | None]:
    """Validate and return only the whitelisted union member for data_type."""

    if data_type not in SUPPORTED_DATA_MODELS:
        raise ValueError(f"Nicht unterstützter Google-Health-Datentyp: {data_type}")
    field_name, model_type = SUPPORTED_DATA_MODELS[data_type]
    raw_value = payload.get(field_name)
    if not isinstance(raw_value, dict):
        raise ValueError(f"Datentyp {data_type} fehlt im Datenpunkt.")
    value = model_type.model_validate(raw_value)
    source_raw = payload.get("dataSource")
    source = GoogleDataSource.model_validate(source_raw) if isinstance(source_raw, dict) else None
    external_name = payload.get("name") or payload.get("dataPointName")
    if external_name is not None and (not isinstance(external_name, str) or len(external_name) > 512):
        raise ValueError("Ungültiger externer Datenpunktname.")
    return value, source, external_name
