from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AVENTO_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Avento API"
    environment: str = "development"
    database_url: str = "sqlite:///./avento.db"
    secret_key: str = Field(default="development-only-secret-change-me-please", min_length=32)
    bootstrap_invite_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AVENTO_BOOTSTRAP_INVITE_CODE", "BOOTSTRAP_INVITE_CODE"),
    )
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 20 * 1024 * 1024
    auto_create_schema: bool = True

    weather_provider: str = "open_meteo"
    weather_timeout_seconds: float = 8.0

    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AVENTO_OPENAI_API_KEY", "OPENAI_API_KEY", "AVENTO_AI_API_KEY"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("AVENTO_OPENAI_BASE_URL", "OPENAI_BASE_URL", "AVENTO_AI_BASE_URL"),
    )
    openai_model: str = Field(
        default="gpt-5.4-mini",
        validation_alias=AliasChoices("AVENTO_OPENAI_MODEL", "OPENAI_MODEL", "AVENTO_AI_MODEL"),
    )
    ai_timeout_seconds: float = 20.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
