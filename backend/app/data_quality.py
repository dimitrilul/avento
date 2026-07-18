from __future__ import annotations

from collections import Counter
from typing import Any


def assess_track_quality(points: list[dict[str, Any]], *, distance_m: float, duration_s: float) -> list[dict[str, Any]]:
    """Return stable, user-facing quality findings for an imported track."""
    flags: list[dict[str, Any]] = []
    if not points:
        flags.append({"code": "missing_track", "severity": "error", "message": "Es wurden keine Trackpunkte aufgezeichnet.", "fields": ["route", "statistics"]})
        return flags

    timestamps = [point.get("time") for point in points if point.get("time")]
    if len(timestamps) != len(points):
        flags.append({"code": "missing_timestamps", "severity": "warning", "message": "Ein Teil der Trackpunkte hat keinen Zeitstempel.", "fields": ["duration", "speed"]})
    if len(timestamps) > 1 and any(str(left) >= str(right) for left, right in zip(timestamps, timestamps[1:])):
        flags.append({"code": "invalid_timestamps", "severity": "error", "message": "Zeitstempel sind nicht streng aufsteigend.", "fields": ["duration", "speed", "statistics"]})

    gps_points = [point for point in points if point.get("latitude") is not None and point.get("longitude") is not None]
    if not gps_points:
        flags.append({"code": "missing_gps", "severity": "warning", "message": "Für diese Aktivität sind keine GPS-Koordinaten vorhanden.", "fields": ["route", "map"]})
    elif len(gps_points) < max(2, len(points) // 2):
        flags.append({"code": "gps_gaps", "severity": "warning", "message": "GPS-Daten fehlen für einen relevanten Teil der Strecke.", "fields": ["route", "map", "distance"]})

    speeds = [float(point["speed_mps"]) for point in points if isinstance(point.get("speed_mps"), (int, float))]
    if any(speed < 0 or speed > 45 for speed in speeds):
        flags.append({"code": "unrealistic_speed", "severity": "error", "message": "Mindestens ein Geschwindigkeitswert liegt außerhalb eines plausiblen Bereichs.", "fields": ["speed", "statistics"]})
    if distance_m <= 0 or duration_s <= 0:
        flags.append({"code": "incomplete_summary", "severity": "warning", "message": "Distanz oder Dauer konnte nicht vollständig bestimmt werden.", "fields": ["distance", "duration", "statistics"]})

    sensor_counts = Counter(
        key
        for point in points
        for key in ("heart_rate_bpm", "cadence_rpm", "power_w")
        if point.get(key) is not None
    )
    if not sensor_counts.get("heart_rate_bpm"):
        flags.append({"code": "missing_heart_rate", "severity": "info", "message": "Keine Herzfrequenzdaten vorhanden.", "fields": ["heart_rate", "training_context"]})
    if not sensor_counts.get("power_w"):
        flags.append({"code": "missing_power", "severity": "info", "message": "Keine Leistungsdaten vorhanden.", "fields": ["power", "training_context"]})
    return flags


def provenance_for_activity(points: list[dict[str, Any]], flags: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "distance": {"source": "TCX/FIT/GPX", "method": "kumulierte Trackdistanz", "quality": "estimated" if any(flag["code"] == "gps_gaps" for flag in flags) else "measured"},
        "duration": {"source": "TCX/FIT/GPX", "method": "Zeitspanne der Trackpunkte", "quality": "incomplete" if any(flag["code"] == "invalid_timestamps" for flag in flags) else "measured"},
        "route": {"source": "GPS", "method": "Trackpunkte", "quality": "missing" if not any(point.get("latitude") is not None and point.get("longitude") is not None for point in points) else "measured"},
        "heart_rate": {"source": "Herzfrequenzsensor", "method": "vorhandene Messpunkte", "quality": "missing" if not any(point.get("heart_rate_bpm") is not None for point in points) else "measured"},
    }
