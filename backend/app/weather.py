from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .config import Settings


class WeatherProvider(ABC):
    name: str

    @abstractmethod
    def weather_at(self, latitude: float, longitude: float, started_at: datetime) -> dict[str, Any] | None:
        raise NotImplementedError


class DisabledWeatherProvider(WeatherProvider):
    name = "disabled"

    def weather_at(self, latitude: float, longitude: float, started_at: datetime) -> dict[str, Any] | None:
        return None


class OpenMeteoWeatherProvider(WeatherProvider):
    name = "open_meteo"
    hourly_fields = [
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
        "wind_direction_10m",
        "relative_humidity_2m",
    ]

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    def weather_at(self, latitude: float, longitude: float, started_at: datetime) -> dict[str, Any] | None:
        started_at = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        started_at = started_at.astimezone(timezone.utc)
        date = started_at.date()
        historical = date < (datetime.now(timezone.utc).date() - timedelta(days=5))
        url = "https://archive-api.open-meteo.com/v1/archive" if historical else "https://api.open-meteo.com/v1/forecast"
        response = httpx.get(
            url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": date.isoformat(),
                "end_date": date.isoformat(),
                "hourly": ",".join(self.hourly_fields),
                "timezone": "UTC",
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        hourly = response.json().get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return None
        candidates = [datetime.fromisoformat(value).replace(tzinfo=timezone.utc) for value in times]
        index = min(range(len(candidates)), key=lambda item: abs((candidates[item] - started_at).total_seconds()))

        def value(field: str) -> Any:
            values = hourly.get(field, [])
            return values[index] if index < len(values) else None

        return {
            "provider": self.name,
            "observed_at": candidates[index].isoformat().replace("+00:00", "Z"),
            "temperature_c": value("temperature_2m"),
            "apparent_temperature_c": value("apparent_temperature"),
            "precipitation_mm": value("precipitation"),
            "weather_code": value("weather_code"),
            "wind_speed_kmh": value("wind_speed_10m"),
            "wind_direction_deg": value("wind_direction_10m"),
            "humidity_percent": value("relative_humidity_2m"),
        }


def get_weather_provider(settings: Settings) -> WeatherProvider:
    if settings.weather_provider.lower() == "open_meteo":
        return OpenMeteoWeatherProvider(settings.weather_timeout_seconds)
    return DisabledWeatherProvider()

