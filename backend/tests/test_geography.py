from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.geography import (
    BACKFILL_REQUEST_INTERVAL_SECONDS,
    DEFAULT_USER_AGENT,
    MAXIMUM_REVERSE_GEOCODING_SAMPLES,
    NominatimReverseGeocoder,
    RequestRateLimiter,
    reverse_geocode_track,
    sample_track_points,
)


def _track(count: int = 21) -> list[dict[str, Any]]:
    return [
        {
            "latitude": 52.0 + index * 0.001,
            "longitude": 13.0 + index * 0.001,
            "distance_m": index * 500,
            "time": f"2026-06-01T08:{index:02d}:00Z",
            "heart_rate_bpm": 120 + index,
        }
        for index in range(count)
    ]


def test_sample_track_points_is_sparse_bounded_and_coordinate_only():
    points = _track(30)
    points.insert(4, {"latitude": float("nan"), "longitude": 13.0, "distance_m": 1_500})
    points.insert(5, {"latitude": 95, "longitude": 13.0, "distance_m": 1_600})

    samples = sample_track_points(points, maximum_samples=100, minimum_spacing_m=0)

    assert len(samples) == MAXIMUM_REVERSE_GEOCODING_SAMPLES
    assert samples[0]["point_index"] == 0
    assert samples[-1]["point_index"] == len(points) - 1
    assert all(set(sample) == {"point_index", "latitude", "longitude"} for sample in samples)
    assert all("heart_rate_bpm" not in sample and "time" not in sample for sample in samples)


def test_sample_track_points_avoids_redundant_queries_on_a_short_route():
    samples = sample_track_points(
        _track(3),
        maximum_samples=8,
        minimum_spacing_m=2_000,
    )

    assert len(samples) == 1
    assert samples[0]["point_index"] == 1


class _FixtureGeocoder:
    provider = "fixture-geocoder"
    attribution = "Fixture data"

    def __init__(self) -> None:
        self.calls: list[tuple[float, float]] = []

    def reverse(self, latitude: float, longitude: float) -> dict[str, Any]:
        self.calls.append((latitude, longitude))
        if len(self.calls) == 1:
            return {
                "address": {
                    "village": "  Müggelheim ",
                    "municipality": "Berlin",
                    "state": " Berlin ",
                    "country": "Deutschland",
                    "country_code": "de",
                }
            }
        if len(self.calls) == 2:
            return {
                "address": {
                    "city": "Potsdam",
                    "state": "Brandenburg",
                    "country": "Deutschland",
                    "country_code": "DE",
                }
            }
        return {
            "address": {
                "town": "Werder (Havel)",
                "state": "Brandenburg",
                "country": "Deutschland",
                "country_code": "de",
            }
        }


def test_reverse_geocode_track_normalizes_deduplicates_and_attributes_places():
    geocoder = _FixtureGeocoder()
    settings = SimpleNamespace(
        reverse_geocoder=geocoder,
        reverse_geocoding_max_samples=3,
        reverse_geocoding_minimum_spacing_m=0,
    )

    places = reverse_geocode_track(_track(3), settings)

    assert len(geocoder.calls) == 3
    assert [(place["place_type"], place["name"]) for place in places] == [
        ("village", "Müggelheim"),
        ("city", "Potsdam"),
        ("city", "Werder (Havel)"),
        ("municipality", "Berlin"),
        ("state", "Berlin"),
        ("state", "Brandenburg"),
        ("country", "Deutschland"),
    ]
    assert all(
        set(place)
        == {
            "place_type",
            "name",
            "region",
            "country",
            "country_code",
            "provider",
            "attribution",
        }
        for place in places
    )
    assert all(place["provider"] == "fixture-geocoder" for place in places)
    assert all(place["attribution"] == "Fixture data" for place in places)
    assert places[0]["region"] == "Berlin"
    assert places[0]["country_code"] == "DE"


def test_reverse_geocode_track_is_unavailable_without_configuration(monkeypatch: pytest.MonkeyPatch):
    def unexpected_request(*args: Any, **kwargs: Any) -> httpx.Response:
        raise AssertionError("Ohne Konfiguration darf keine externe Anfrage erfolgen.")

    monkeypatch.setattr(httpx, "get", unexpected_request)

    assert reverse_geocode_track(_track(), SimpleNamespace()) == []


def test_reverse_geocode_track_stops_after_failures_without_raising():
    class FailingGeocoder:
        provider = "failing"
        calls = 0

        def reverse(self, latitude: float, longitude: float) -> None:
            self.calls += 1
            raise httpx.TimeoutException("timeout")

    geocoder = FailingGeocoder()
    settings = SimpleNamespace(
        reverse_geocoder=geocoder,
        reverse_geocoding_max_samples=8,
        reverse_geocoding_minimum_spacing_m=0,
        reverse_geocoding_maximum_failures=2,
    )

    assert reverse_geocode_track(_track(), settings) == []
    assert geocoder.calls == 2


def test_nominatim_client_uses_stable_identity_and_reusable_minimal_cache():
    calls: list[dict[str, Any]] = []
    cache: dict[str, Any] = {}

    def requester(url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={
                "lat": "52.50001",
                "lon": "13.40001",
                "display_name": "Unnötige genaue Adresse",
                "address": {
                    "road": "Nicht speichern",
                    "city": "Berlin",
                    "state": "Berlin",
                    "country": "Deutschland",
                    "country_code": "de",
                },
            },
            request=httpx.Request("GET", url),
        )

    first_client = NominatimReverseGeocoder(
        "https://geo.example.test/api",
        cache=cache,
        requester=requester,
    )
    first = first_client.reverse(52.50001, 13.40001)
    second_client = NominatimReverseGeocoder(
        "https://geo.example.test/api",
        cache=cache,
        requester=lambda *args, **kwargs: pytest.fail("Cache wurde nicht wiederverwendet"),
    )
    second = second_client.reverse(52.50002, 13.40002)

    assert first == second == {
        "address": {
            "city": "Berlin",
            "state": "Berlin",
            "country": "Deutschland",
            "country_code": "de",
        }
    }
    assert len(calls) == 1
    assert calls[0]["url"] == "https://geo.example.test/api/reverse"
    assert calls[0]["headers"]["User-Agent"] == DEFAULT_USER_AGENT
    assert calls[0]["params"]["lat"] == "52.5000"
    assert calls[0]["params"]["lon"] == "13.4000"
    assert all("road" not in cached["address"] for cached in cache.values())


def test_rate_limiter_serializes_request_starts_at_one_per_second():
    current_time = [100.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        current_time[0] += seconds

    limiter = RequestRateLimiter(clock=lambda: current_time[0], sleeper=sleep)
    limiter.run(lambda: None)
    current_time[0] += 0.25
    limiter.run(lambda: None)

    assert sleeps == [pytest.approx(0.75)]


def test_backfill_mode_enforces_four_requests_per_minute():
    intervals: list[float] = []

    class RecordingLimiter:
        def run(self, request: Any, *, minimum_interval_seconds: float) -> Any:
            intervals.append(minimum_interval_seconds)
            return request()

    def requester(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={"address": {"city": "Berlin", "country": "Deutschland", "country_code": "de"}},
            request=httpx.Request("GET", url),
        )

    settings = SimpleNamespace(
        reverse_geocoding_provider="nominatim",
        reverse_geocoding_base_url="https://geo.example.test",
        reverse_geocoding_backfill_mode=True,
        reverse_geocoding_rate_limiter=RecordingLimiter(),
        reverse_geocoding_requester=requester,
        reverse_geocoding_max_samples=1,
        reverse_geocoding_minimum_spacing_m=0,
    )

    places = reverse_geocode_track(_track(1), settings)

    assert places[0]["name"] == "Berlin"
    assert intervals == [BACKFILL_REQUEST_INTERVAL_SECONDS]
