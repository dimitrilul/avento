from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from app.weather import OpenMeteoWeatherProvider, WeatherProvider
from app.weather_classification import classify_route_weather


@pytest.mark.parametrize(
    ("sample", "expected"),
    [
        ({"precipitation_mm": 0.4, "weather_code": 0}, "light"),
        ({"precipitation_mm": 3.0, "weather_code": 0}, "moderate"),
        ({"precipitation_mm": 8.0, "weather_code": 0}, "heavy"),
        ({"precipitation_mm": 0.0, "weather_code": 61}, "light"),
        ({"precipitation_mm": 0.1, "weather_code": 65}, "heavy"),
    ],
)
def test_classifies_light_moderate_and_heavy_rain(sample: dict[str, Any], expected: str):
    classification = classify_route_weather([sample])

    assert classification["rain_intensity"] == expected
    assert classification["rain_sample_count"] == 1


def test_rain_counts_when_it_starts_during_the_ride():
    route_samples = [
        {
            "point_index": 6,
            "track_time": "2026-06-01T09:00:00Z",
            "precipitation_mm": 3.2,
            "weather_code": 63,
        },
        {
            "point_index": 0,
            "track_time": "2026-06-01T08:00:00Z",
            "precipitation_mm": 0,
            "weather_code": 1,
        },
        {
            "point_index": 3,
            "track_time": "2026-06-01T08:30:00Z",
            "precipitation_mm": 0.7,
            "weather_code": 61,
        },
    ]

    classification = classify_route_weather(route_samples)

    assert classification["rain_intensity"] == "moderate"
    assert classification["rain_started_during_ride"] is True
    assert classification["first_rain_point_index"] == 3
    assert classification["first_rain_track_time"] == "2026-06-01T08:30:00Z"
    assert classification["max_precipitation_mm"] == 3.2


def test_classifies_thunderstorm_ice_and_storm_as_challenge_risks():
    route_samples = [
        {"point_index": 0, "weather_code": 95, "precipitation_mm": 2.0},
        {"point_index": 1, "weather_code": 66, "temperature_c": 1.0},
        {"point_index": 2, "weather_code": 0, "wind_gusts_kmh": 65.0},
    ]

    classification = classify_route_weather(route_samples)

    assert classification["thunderstorm"] is True
    assert classification["ice_risk"] is True
    assert classification["storm"] is True
    assert classification["risk_flags"] == ["thunderstorm", "ice", "storm"]
    assert classification["has_risky_conditions"] is True
    assert classification["safe_for_challenges"] is False


def test_wet_freezing_conditions_are_ice_risk_without_a_freezing_wmo_code():
    classification = classify_route_weather(
        [{"weather_code": 61, "precipitation_mm": 0.2, "temperature_c": -0.1}]
    )

    assert classification["ice_risk"] is True
    assert classification["safe_for_challenges"] is False


def test_snow_precipitation_is_not_misclassified_as_rain():
    classification = classify_route_weather(
        [{"weather_code": 73, "precipitation_mm": 3.0, "temperature_c": -2.0}]
    )

    assert classification["rain_intensity"] == "none"
    assert classification["ice_risk"] is True
    assert classification["max_precipitation_mm"] == 3.0


def test_empty_or_malformed_samples_are_safe_and_deterministic():
    classification = classify_route_weather(
        [{"weather_code": "invalid", "precipitation_mm": float("nan"), "wind_speed_kmh": None}]
    )

    assert classification == {
        "sample_count": 1,
        "rain_intensity": "none",
        "rain_started_during_ride": False,
        "rain_sample_count": 0,
        "first_rain_point_index": None,
        "first_rain_track_time": None,
        "max_precipitation_mm": None,
        "thunderstorm": False,
        "ice_risk": False,
        "storm": False,
        "risk_flags": [],
        "has_risky_conditions": False,
        "safe_for_challenges": True,
    }


def test_weather_provider_samples_route_time_so_later_rain_is_detected():
    class DeterministicProvider(WeatherProvider):
        name = "fixture"

        def weather_at(
            self,
            latitude: float,
            longitude: float,
            started_at: datetime,
        ) -> dict[str, Any]:
            raining = started_at.hour > 8 or started_at.minute >= 30
            return {
                "provider": self.name,
                "observed_at": started_at.isoformat(),
                "precipitation_mm": 3.0 if raining else 0.0,
                "weather_code": 63 if raining else 0,
            }

    times = ("2026-06-01T08:00:00Z", "2026-06-01T08:30:00Z", "2026-06-01T09:00:00Z")
    points = [
        {
            "latitude": 52.5 + index * 0.01,
            "longitude": 13.4,
            "distance_m": index * 10_000,
            "time": times[index],
        }
        for index in range(3)
    ]

    samples = DeterministicProvider().weather_along_route(points, maximum_samples=3)
    classification = classify_route_weather(samples)

    assert [sample["point_index"] for sample in samples] == [0, 1, 2]
    assert classification["rain_intensity"] == "moderate"
    assert classification["rain_started_during_ride"] is True


def test_open_meteo_requests_and_exposes_wind_gusts(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> httpx.Response:
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-06-01T08:00"],
                    "temperature_2m": [10.0],
                    "apparent_temperature": [9.0],
                    "precipitation": [0.0],
                    "rain": [0.0],
                    "weather_code": [0],
                    "wind_speed_10m": [20.0],
                    "wind_gusts_10m": [66.0],
                    "wind_direction_10m": [270],
                    "relative_humidity_2m": [70],
                }
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("app.weather.httpx.get", fake_get)
    weather = OpenMeteoWeatherProvider(timeout=2).weather_at(
        52.5,
        13.4,
        datetime(2026, 6, 1, 8, tzinfo=timezone.utc),
    )

    assert "rain" in captured["params"]["hourly"]
    assert "wind_gusts_10m" in captured["params"]["hourly"]
    assert weather is not None
    assert weather["wind_gusts_kmh"] == 66.0
    assert classify_route_weather([weather])["storm"] is True
