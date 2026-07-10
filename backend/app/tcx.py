from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from defusedxml import ElementTree as DefusedET


class TcxError(ValueError):
    """Raised when a TCX document cannot be safely interpreted."""


@dataclass(slots=True)
class ParsedActivity:
    started_at: datetime
    ended_at: datetime
    activity_type: str
    track_points: list[dict[str, Any]]
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


def default_hr_zones(hr_max: int) -> list[dict[str, Any]]:
    colors = ["#607D8B", "#4CAF50", "#FFEB3B", "#FF9800", "#F44336"]
    names = ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"]
    bounds = [0.0, 0.6, 0.7, 0.8, 0.9, 1.01]
    zones: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        minimum = 30 if index == 0 else round(hr_max * bounds[index])
        maximum = hr_max if index == 4 else round(hr_max * bounds[index + 1]) - 1
        zones.append({"name": name, "min_bpm": minimum, "max_bpm": maximum, "color": colors[index]})
    return zones


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: Any, name: str) -> Any | None:
    return next((child for child in element if _local_name(child.tag) == name), None)


def _descendant_text(element: Any, names: tuple[str, ...]) -> str | None:
    for descendant in element.iter():
        if _local_name(descendant.tag) in names and descendant.text:
            return descendant.text.strip()
    return None


def _float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        value = float(text)
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def _int(text: str | None) -> int | None:
    value = _float(text)
    return round(value) if value is not None else None


def _time(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    delta_p = math.radians(lat2 - lat1)
    delta_l = math.radians(lon2 - lon1)
    a = math.sin(delta_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(delta_l / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _mean(values: list[int | float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def parse_tcx(data: bytes, zones: list[dict[str, Any]], fallback_hr_max: int = 190) -> ParsedActivity:
    try:
        root = DefusedET.fromstring(data)
    except Exception as exc:
        raise TcxError("Die Datei ist kein gültiges oder sicheres TCX-Dokument.") from exc
    if _local_name(root.tag) != "TrainingCenterDatabase":
        raise TcxError("Die XML-Datei ist keine Garmin-TCX-Datei.")

    activity_element = next((node for node in root.iter() if _local_name(node.tag) == "Activity"), None)
    if activity_element is None:
        raise TcxError("Die TCX-Datei enthält keine Aktivität.")
    sport = str(activity_element.attrib.get("Sport", "cycling")).lower()

    raw_points: list[dict[str, Any]] = []
    for point in (node for node in activity_element.iter() if _local_name(node.tag) == "Trackpoint"):
        time_element = _child(point, "Time")
        point_time = _time(time_element.text.strip() if time_element is not None and time_element.text else None)
        if point_time is None:
            continue
        position = _child(point, "Position")
        latitude = longitude = None
        if position is not None:
            lat_element = _child(position, "LatitudeDegrees")
            lon_element = _child(position, "LongitudeDegrees")
            latitude = _float(lat_element.text.strip() if lat_element is not None and lat_element.text else None)
            longitude = _float(lon_element.text.strip() if lon_element is not None and lon_element.text else None)
            if latitude is not None and not -90 <= latitude <= 90:
                latitude = None
            if longitude is not None and not -180 <= longitude <= 180:
                longitude = None

        altitude_element = _child(point, "AltitudeMeters")
        distance_element = _child(point, "DistanceMeters")
        hr_element = _child(point, "HeartRateBpm")
        cadence_element = _child(point, "Cadence")
        raw_points.append(
            {
                "time_value": point_time,
                "time": point_time.isoformat().replace("+00:00", "Z"),
                "latitude": latitude,
                "longitude": longitude,
                "altitude_m": _float(altitude_element.text.strip() if altitude_element is not None and altitude_element.text else None),
                "source_distance_m": _float(distance_element.text.strip() if distance_element is not None and distance_element.text else None),
                "heart_rate_bpm": _int(_descendant_text(hr_element, ("Value",)) if hr_element is not None else None),
                "cadence_rpm": _int(cadence_element.text.strip() if cadence_element is not None and cadence_element.text else None),
                "power_w": _int(_descendant_text(point, ("Watts", "Power"))),
                "source_speed_mps": _float(_descendant_text(point, ("Speed",))),
            }
        )

    if len(raw_points) < 2:
        raise TcxError("Die TCX-Datei enthält zu wenige Trackpunkte mit Zeitstempel.")
    raw_points.sort(key=lambda point: point["time_value"])
    if not zones:
        zones = default_hr_zones(fallback_hr_max)

    distance = 0.0
    moving_time = 0.0
    elevation_gain = 0.0
    speeds: list[float] = []
    zone_seconds = {str(zone["name"]): 0.0 for zone in zones}
    previous_altitude: float | None = None
    output_points: list[dict[str, Any]] = []

    for index, point in enumerate(raw_points):
        segment_distance = 0.0
        delta_seconds = 0.0
        if index:
            previous = raw_points[index - 1]
            delta_seconds = (point["time_value"] - previous["time_value"]).total_seconds()
            source_current = point["source_distance_m"]
            source_previous = previous["source_distance_m"]
            if source_current is not None and source_previous is not None and 0 <= source_current - source_previous <= 10_000:
                segment_distance = source_current - source_previous
            elif all(previous.get(key) is not None and point.get(key) is not None for key in ("latitude", "longitude")):
                segment_distance = _haversine(previous["latitude"], previous["longitude"], point["latitude"], point["longitude"])
            distance += max(0.0, segment_distance)

            speed = point["source_speed_mps"]
            if speed is None and delta_seconds > 0:
                speed = segment_distance / delta_seconds
            if speed is not None and 0 <= speed <= 50:
                speeds.append(speed)
                if 0 < delta_seconds <= 120 and speed >= 0.5:
                    moving_time += delta_seconds

            if 0 < delta_seconds <= 300 and point["heart_rate_bpm"] is not None:
                heart_rate = point["heart_rate_bpm"]
                matching = next((zone for zone in zones if int(zone["min_bpm"]) <= heart_rate <= int(zone["max_bpm"])), None)
                if matching:
                    zone_seconds[str(matching["name"])] += delta_seconds

        altitude = point["altitude_m"]
        if altitude is not None and previous_altitude is not None:
            gain = altitude - previous_altitude
            if 1 <= gain <= 100:
                elevation_gain += gain
        if altitude is not None:
            previous_altitude = altitude

        speed_value = point["source_speed_mps"]
        if speed_value is None and index and delta_seconds > 0:
            speed_value = segment_distance / delta_seconds
        output_points.append(
            {
                "time": point["time"],
                "latitude": point["latitude"],
                "longitude": point["longitude"],
                "altitude_m": altitude,
                "distance_m": round(distance, 2),
                "heart_rate_bpm": point["heart_rate_bpm"],
                "cadence_rpm": point["cadence_rpm"],
                "power_w": point["power_w"],
                "speed_mps": round(speed_value, 3) if speed_value is not None and 0 <= speed_value <= 50 else None,
            }
        )

    started_at = raw_points[0]["time_value"]
    ended_at = raw_points[-1]["time_value"]
    duration = max(0.0, (ended_at - started_at).total_seconds())
    moving_time = min(duration, moving_time)
    hr_values = [point["heart_rate_bpm"] for point in raw_points if point["heart_rate_bpm"] is not None]
    cadence_values = [point["cadence_rpm"] for point in raw_points if point["cadence_rpm"] is not None]
    power_values = [point["power_w"] for point in raw_points if point["power_w"] is not None]

    weighted_minutes = sum(zone_seconds[str(zone["name"])] / 60 * (index + 1) for index, zone in enumerate(zones))
    return ParsedActivity(
        started_at=started_at,
        ended_at=ended_at,
        activity_type="cycling" if sport in {"biking", "cycling", "bike"} else sport,
        track_points=output_points,
        distance_m=round(distance, 2),
        duration_s=round(duration, 2),
        moving_time_s=round(moving_time, 2),
        pause_time_s=round(max(0.0, duration - moving_time), 2),
        avg_speed_mps=round(distance / moving_time, 3) if moving_time else 0.0,
        max_speed_mps=round(max(speeds), 3) if speeds else 0.0,
        elevation_gain_m=round(elevation_gain, 2),
        avg_hr_bpm=_mean(hr_values),
        max_hr_bpm=max(hr_values) if hr_values else None,
        avg_cadence_rpm=_mean(cadence_values),
        max_cadence_rpm=max(cadence_values) if cadence_values else None,
        avg_power_w=_mean(power_values),
        max_power_w=max(power_values) if power_values else None,
        training_load=round(weighted_minutes, 2),
        hr_zone_seconds={key: round(value, 2) for key, value in zone_seconds.items()},
    )
