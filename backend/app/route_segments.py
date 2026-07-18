from __future__ import annotations

import math
from typing import Any


def _coordinates(points: list[dict[str, Any]]) -> list[tuple[float, float]]:
    return [(float(point["latitude"]), float(point["longitude"])) for point in points if point.get("latitude") is not None and point.get("longitude") is not None]


def route_signature(points: list[dict[str, Any]]) -> list[str]:
    """Quantize GPS coordinates so small GPS drift does not split a route."""
    coordinates = _coordinates(points)
    if not coordinates: return []
    step = 0.0015  # roughly 100–170 m depending on latitude
    return list(dict.fromkeys(f"{round(latitude / step)}:{round(longitude / step)}" for latitude, longitude in coordinates[::max(1, len(coordinates) // 80)]))


def route_similarity(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> float:
    first, second = set(route_signature(left)), set(route_signature(right))
    if not first or not second: return 0.0
    return round(2 * len(first & second) / (len(first) + len(second)), 3)


def segment_metrics(points: list[dict[str, Any]], start_m: float, end_m: float) -> dict[str, Any]:
    selected = [point for point in points if start_m <= float(point.get("distance_m") or 0) <= end_m]
    if len(selected) < 2: return {"point_count": len(selected), "distance_m": max(0, end_m - start_m), "duration_s": None, "avg_speed_mps": None, "elevation_gain_m": None, "avg_heart_rate_bpm": None}
    times = [str(point["time"]) for point in selected if point.get("time")]
    duration = None
    if len(times) >= 2:
        from datetime import datetime
        try: duration = max(0, (datetime.fromisoformat(times[-1].replace("Z", "+00:00")) - datetime.fromisoformat(times[0].replace("Z", "+00:00"))).total_seconds())
        except ValueError: pass
    elevations = [float(point["altitude_m"]) for point in selected if point.get("altitude_m") is not None]
    heart_rates = [float(point["heart_rate_bpm"]) for point in selected if point.get("heart_rate_bpm") is not None]
    return {"point_count": len(selected), "distance_m": max(0, end_m - start_m), "duration_s": duration, "avg_speed_mps": (max(0, end_m - start_m) / duration if duration else None), "elevation_gain_m": sum(max(0, current - previous) for previous, current in zip(elevations, elevations[1:])), "avg_heart_rate_bpm": sum(heart_rates) / len(heart_rates) if heart_rates else None}
