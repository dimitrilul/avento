from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from math import isfinite
from typing import Any, TypedDict


LIGHT_RAIN_THRESHOLD_MM = 0.0
MODERATE_RAIN_THRESHOLD_MM = 2.5
HEAVY_RAIN_THRESHOLD_MM = 7.5
STORM_WIND_THRESHOLD_KMH = 62.0
STORM_GUST_THRESHOLD_KMH = 65.0
FREEZING_TEMPERATURE_C = 0.0

_RAIN_LEVELS = ("none", "light", "moderate", "heavy")
_RAIN_LEVEL_BY_CODE = {
    **{code: "light" for code in (51, 56, 61, 66, 80)},
    **{code: "moderate" for code in (53, 63, 81, 95)},
    **{code: "heavy" for code in (55, 57, 65, 67, 82, 96, 99)},
}
_THUNDERSTORM_CODES = {95, 96, 99}
_SNOW_CODES = {71, 73, 75, 77, 85, 86}
_ICE_CODES = {
    48,  # depositing rime fog
    56,
    57,  # freezing drizzle
    66,
    67,  # freezing rain
    71,
    73,
    75,
    77,  # snow and snow grains
    85,
    86,  # snow showers
}


class RouteWeatherClassification(TypedDict):
    sample_count: int
    rain_intensity: str
    rain_started_during_ride: bool
    rain_sample_count: int
    first_rain_point_index: int | None
    first_rain_track_time: str | None
    max_precipitation_mm: float | None
    thunderstorm: bool
    ice_risk: bool
    storm: bool
    risk_flags: list[str]
    has_risky_conditions: bool
    safe_for_challenges: bool


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _first_number(sample: Mapping[str, Any], fields: tuple[str, ...]) -> float | None:
    for field in fields:
        value = _number(sample.get(field))
        if value is not None:
            return value
    return None


def _weather_code(sample: Mapping[str, Any]) -> int | None:
    value = _number(sample.get("weather_code"))
    if value is None or not value.is_integer():
        return None
    code = int(value)
    return code if 0 <= code <= 99 else None


def _precipitation_mm(sample: Mapping[str, Any]) -> float | None:
    value = _first_number(sample, ("precipitation_mm", "precipitation"))
    if value is None:
        value = _first_number(sample, ("rain_mm", "rain"))
    return max(0.0, value) if value is not None else None


def _rain_mm(sample: Mapping[str, Any]) -> float | None:
    direct_rain = _first_number(sample, ("rain_mm", "rain"))
    if direct_rain is not None:
        return max(0.0, direct_rain)
    if _weather_code(sample) in _SNOW_CODES:
        return 0.0
    return _precipitation_mm(sample)


def _rain_level(sample: Mapping[str, Any]) -> str:
    rain = _rain_mm(sample)
    if rain is None or rain <= LIGHT_RAIN_THRESHOLD_MM:
        amount_level = "none"
    elif rain < MODERATE_RAIN_THRESHOLD_MM:
        amount_level = "light"
    elif rain < HEAVY_RAIN_THRESHOLD_MM:
        amount_level = "moderate"
    else:
        amount_level = "heavy"
    code_level = _RAIN_LEVEL_BY_CODE.get(_weather_code(sample), "none")
    return max((amount_level, code_level), key=_RAIN_LEVELS.index)


def _parsed_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _ordered_samples(route_samples: Any) -> list[Mapping[str, Any]]:
    source: Any = route_samples
    if isinstance(route_samples, Mapping):
        nested = route_samples.get("route_weather_samples")
        source = nested if isinstance(nested, (list, tuple)) else [route_samples]
    if not isinstance(source, Iterable) or isinstance(source, (str, bytes)):
        return []
    samples = [sample for sample in source if isinstance(sample, Mapping)]
    indexes = [_number(sample.get("point_index")) for sample in samples]
    if samples and all(index is not None for index in indexes):
        return [
            sample
            for _, sample in sorted(
                enumerate(samples),
                key=lambda item: (float(indexes[item[0]] or 0), item[0]),
            )
        ]
    times = [_parsed_time(sample.get("track_time") or sample.get("observed_at")) for sample in samples]
    if samples and all(observed_at is not None for observed_at in times):
        return [
            sample
            for _, sample in sorted(
                enumerate(samples),
                key=lambda item: (times[item[0]], item[0]),
            )
        ]
    return samples


def _has_dry_evidence(sample: Mapping[str, Any]) -> bool:
    rain = _rain_mm(sample)
    code = _weather_code(sample)
    return (rain is not None or code is not None) and _rain_level(sample) == "none"


def classify_route_weather(
    route_samples: Any,
    *,
    storm_wind_threshold_kmh: float = STORM_WIND_THRESHOLD_KMH,
    storm_gust_threshold_kmh: float = STORM_GUST_THRESHOLD_KMH,
    freezing_temperature_c: float = FREEZING_TEMPERATURE_C,
) -> RouteWeatherClassification:
    """Classify rain and unsafe conditions across time/space-matched route samples."""

    samples = _ordered_samples(route_samples)
    wind_threshold = max(0.1, _number(storm_wind_threshold_kmh) or STORM_WIND_THRESHOLD_KMH)
    gust_threshold = max(0.1, _number(storm_gust_threshold_kmh) or STORM_GUST_THRESHOLD_KMH)
    freezing_threshold = _number(freezing_temperature_c)
    freezing_threshold = FREEZING_TEMPERATURE_C if freezing_threshold is None else freezing_threshold
    rain_levels = [_rain_level(sample) for sample in samples]
    rain_intensity = max(rain_levels, key=_RAIN_LEVELS.index, default="none")
    rain_positions = [index for index, level in enumerate(rain_levels) if level != "none"]
    first_rain_position = rain_positions[0] if rain_positions else None
    rain_started_during_ride = bool(
        first_rain_position is not None
        and first_rain_position > 0
        and any(_has_dry_evidence(sample) for sample in samples[:first_rain_position])
    )

    precipitation_values = [
        precipitation
        for sample in samples
        if (precipitation := _precipitation_mm(sample)) is not None
    ]
    weather_codes = [_weather_code(sample) for sample in samples]
    thunderstorm = any(code in _THUNDERSTORM_CODES for code in weather_codes)
    ice_risk = any(code in _ICE_CODES for code in weather_codes)
    if not ice_risk:
        ice_risk = any(
            (temperature := _first_number(sample, ("temperature_c", "temperature_2m"))) is not None
            and temperature <= freezing_threshold
            and ((_precipitation_mm(sample) or 0) > 0 or _rain_level(sample) != "none")
            for sample in samples
        )

    storm = any(
        (
            (wind := _first_number(sample, ("wind_speed_kmh", "wind_speed_10m"))) is not None
            and wind >= wind_threshold
        )
        or (
            (gust := _first_number(sample, ("wind_gusts_kmh", "wind_gusts_10m"))) is not None
            and gust >= gust_threshold
        )
        for sample in samples
    )
    risk_flags = [
        flag
        for flag, present in (
            ("thunderstorm", thunderstorm),
            ("ice", ice_risk),
            ("storm", storm),
        )
        if present
    ]

    first_rain_sample = samples[first_rain_position] if first_rain_position is not None else None
    first_rain_index = _number(first_rain_sample.get("point_index")) if first_rain_sample else None
    track_time = first_rain_sample.get("track_time") if first_rain_sample else None
    has_risky_conditions = bool(risk_flags)
    return {
        "sample_count": len(samples),
        "rain_intensity": rain_intensity,
        "rain_started_during_ride": rain_started_during_ride,
        "rain_sample_count": len(rain_positions),
        "first_rain_point_index": int(first_rain_index) if first_rain_index is not None else None,
        "first_rain_track_time": track_time if isinstance(track_time, str) else None,
        "max_precipitation_mm": round(max(precipitation_values), 3) if precipitation_values else None,
        "thunderstorm": thunderstorm,
        "ice_risk": ice_risk,
        "storm": storm,
        "risk_flags": risk_flags,
        "has_risky_conditions": has_risky_conditions,
        "safe_for_challenges": not has_risky_conditions,
    }
