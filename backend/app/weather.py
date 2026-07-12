from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .config import Settings


class WeatherProvider(ABC):
    name: str

    @abstractmethod
    def weather_at(self, latitude: float, longitude: float, started_at: datetime) -> dict[str, Any] | None:
        raise NotImplementedError

    def weather_along_route(
        self,
        track_points: list[dict[str, Any]],
        maximum_samples: int = 7,
    ) -> list[dict[str, Any]]:
        candidates: list[tuple[int, dict[str, Any]]] = [
            (index, point)
            for index, point in enumerate(track_points)
            if point.get("latitude") is not None
            and point.get("longitude") is not None
            and point.get("time")
        ]
        if not candidates:
            return []
        count = min(maximum_samples, len(candidates))
        distance_axis = [
            float(point["distance_m"])
            if isinstance(point.get("distance_m"), (int, float))
            else None
            for _, point in candidates
        ]
        if all(value is not None for value in distance_axis) and float(distance_axis[-1] or 0) > float(distance_axis[0] or 0):
            axis = [float(value) for value in distance_axis if value is not None]
        else:
            parsed_times: list[float] = []
            for _, point in candidates:
                try:
                    parsed_times.append(datetime.fromisoformat(str(point["time"]).replace("Z", "+00:00")).timestamp())
                except (TypeError, ValueError):
                    parsed_times = []
                    break
            axis = parsed_times if len(parsed_times) == len(candidates) and parsed_times[-1] > parsed_times[0] else [float(index) for index in range(len(candidates))]
        positions = sorted(set(
            min(
                range(len(axis)),
                key=lambda candidate_index: abs(
                    axis[candidate_index] - (axis[0] + (axis[-1] - axis[0]) * sample_index / max(count - 1, 1))
                ),
            )
            for sample_index in range(count)
        ))
        requests: list[tuple[int, dict[str, Any], datetime]] = []
        for position in positions:
            point_index, point = candidates[position]
            try:
                observed_at = datetime.fromisoformat(str(point["time"]).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            requests.append((point_index, point, observed_at))
        samples: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(requests)))) as executor:
            pending = {
                executor.submit(
                    self.weather_at,
                    float(point["latitude"]),
                    float(point["longitude"]),
                    observed_at,
                ): (point_index, point)
                for point_index, point, observed_at in requests
            }
            for future in as_completed(pending):
                point_index, point = pending[future]
                try:
                    weather = future.result()
                except Exception:
                    weather = None
                if weather:
                    samples.append(
                        {
                            "point_index": point_index,
                            "track_time": point["time"],
                            "latitude": round(float(point["latitude"]), 5),
                            "longitude": round(float(point["longitude"]), 5),
                            **weather,
                        }
                    )
        return sorted(samples, key=lambda sample: int(sample["point_index"]))


class DisabledWeatherProvider(WeatherProvider):
    name = "disabled"

    def weather_at(self, latitude: float, longitude: float, started_at: datetime) -> dict[str, Any] | None:
        return None

    def weather_along_route(
        self,
        track_points: list[dict[str, Any]],
        maximum_samples: int = 7,
    ) -> list[dict[str, Any]]:
        return []


class OpenMeteoWeatherProvider(WeatherProvider):
    name = "open_meteo"
    hourly_fields = [
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "weather_code",
        "wind_speed_10m",
        "wind_gusts_10m",
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
            "rain_mm": value("rain"),
            "weather_code": value("weather_code"),
            "wind_speed_kmh": value("wind_speed_10m"),
            "wind_gusts_kmh": value("wind_gusts_10m"),
            "wind_direction_deg": value("wind_direction_10m"),
            "humidity_percent": value("relative_humidity_2m"),
        }


def get_weather_provider(settings: Settings) -> WeatherProvider:
    if settings.weather_provider.lower() == "open_meteo":
        return OpenMeteoWeatherProvider(settings.weather_timeout_seconds)
    return DisabledWeatherProvider()
