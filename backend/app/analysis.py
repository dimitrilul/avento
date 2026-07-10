from __future__ import annotations

import math
from datetime import datetime
from statistics import mean
from typing import Any, Iterable

from .models import Activity


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None


def _coordinates(point: dict[str, Any]) -> tuple[float, float] | None:
    latitude = _number(point.get("latitude"))
    longitude = _number(point.get("longitude"))
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def bearing_degrees(start: tuple[float, float], end: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    delta_lon = lon2 - lon1
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def route_wind_summary(
    track_points: list[dict[str, Any]],
    samples: list[dict[str, Any]],
) -> dict[str, Any] | None:
    components: list[dict[str, float | int]] = []
    for sample in samples:
        index = int(sample.get("point_index", 0))
        speed = _number(sample.get("wind_speed_kmh"))
        wind_from = _number(sample.get("wind_direction_deg"))
        if speed is None or wind_from is None or not track_points:
            continue
        index = max(0, min(index, len(track_points) - 1))
        current_coordinate = _coordinates(track_points[index])
        origin = current_coordinate
        destination = None
        for offset in range(1, 30):
            next_index = index + offset
            if next_index < len(track_points):
                destination = _coordinates(track_points[next_index])
                if destination and destination != origin:
                    break
        if destination is None and current_coordinate is not None:
            for offset in range(1, 30):
                previous_index = index - offset
                if previous_index < 0:
                    break
                previous_coordinate = _coordinates(track_points[previous_index])
                if previous_coordinate and previous_coordinate != current_coordinate:
                    origin = previous_coordinate
                    destination = current_coordinate
                    break
        if origin is None or destination is None or destination == origin:
            continue
        course = bearing_degrees(origin, destination)
        angle = math.radians((wind_from - course + 180) % 360 - 180)
        signed_headwind = speed * math.cos(angle)
        crosswind = abs(speed * math.sin(angle))
        components.append(
            {
                "point_index": index,
                "distance_m": round(_number(track_points[index].get("distance_m")) or float(index), 1),
                "course_deg": round(course, 1),
                "headwind_component_kmh": round(signed_headwind, 1),
                "crosswind_component_kmh": round(crosswind, 1),
            }
        )
    if not components:
        return None
    components.sort(key=lambda item: int(item["point_index"]))
    for index, component in enumerate(components):
        current_distance = float(component["distance_m"])
        previous_distance = float(components[index - 1]["distance_m"]) if index else current_distance
        next_distance = float(components[index + 1]["distance_m"]) if index + 1 < len(components) else current_distance
        left = max(0.0, current_distance - previous_distance) / 2
        right = max(0.0, next_distance - current_distance) / 2
        component["weight_m"] = round(max(1.0, left + right), 1)
    signed = [float(item["headwind_component_kmh"]) for item in components]
    cross = [float(item["crosswind_component_kmh"]) for item in components]
    weights = [float(item["weight_m"]) for item in components]
    headwind = [max(value, 0.0) for value in signed]
    tailwind = [max(-value, 0.0) for value in signed]
    total_weight = sum(weights)

    def weighted(values: list[float]) -> float:
        return sum(value * weight for value, weight in zip(values, weights)) / total_weight

    signed_average = weighted(signed)
    if signed_average >= 1.5:
        dominant = "headwind"
    elif signed_average <= -1.5:
        dominant = "tailwind"
    elif weighted(cross) >= 3:
        dominant = "crosswind"
    else:
        dominant = "mixed"
    return {
        "dominant": dominant,
        "net_headwind_kmh": round(signed_average, 1),
        "avg_headwind_kmh": round(weighted(headwind), 1),
        "avg_tailwind_kmh": round(weighted(tailwind), 1),
        "avg_crosswind_kmh": round(weighted(cross), 1),
        "headwind_share_percent": round(sum(weight for value, weight in zip(signed, weights) if value > 1) / total_weight * 100),
        "tailwind_share_percent": round(sum(weight for value, weight in zip(signed, weights) if value < -1) / total_weight * 100),
        "samples": components,
    }


def similarity_score(target: Activity, candidate: Activity) -> float:
    def ratio_distance(left: float, right: float, floor: float = 1.0) -> float:
        return abs(math.log(max(left, floor) / max(right, floor)))

    score = ratio_distance(target.distance_m, candidate.distance_m)
    score += ratio_distance(target.moving_time_s, candidate.moving_time_s) * 0.8
    score += ratio_distance(target.elevation_gain_m + 100, candidate.elevation_gain_m + 100) * 0.55
    if target.activity_type != candidate.activity_type:
        score += 0.8
    target_start = next((_coordinates(point) for point in target.track_points or [] if _coordinates(point)), None)
    candidate_start = next((_coordinates(point) for point in candidate.track_points or [] if _coordinates(point)), None)
    if target_start and candidate_start:
        lat_delta = target_start[0] - candidate_start[0]
        lon_delta = target_start[1] - candidate_start[1]
        score += min(math.hypot(lat_delta, lon_delta) * 8, 0.8)
    return score


def find_similar_activities(target: Activity, candidates: Iterable[Activity], limit: int = 7) -> list[Activity]:
    eligible = [candidate for candidate in candidates if candidate.id != target.id]
    return sorted(eligible, key=lambda candidate: similarity_score(target, candidate))[: max(3, min(limit, 10))]


def _activity_wind(activity: Activity) -> float | None:
    route_wind = (activity.weather or {}).get("route_wind") or {}
    return _number(route_wind.get("net_headwind_kmh"))


def comparison_metric(activity: Activity) -> dict[str, Any]:
    speed_kmh = activity.avg_speed_mps * 3.6
    efficiency = speed_kmh / activity.avg_hr_bpm if activity.avg_hr_bpm else None
    return {
        "activity_id": activity.id,
        "title": activity.title,
        "distance_m": round(activity.distance_m, 1),
        "duration_s": round(activity.duration_s, 1),
        "moving_time_s": round(activity.moving_time_s, 1),
        "elevation_gain_m": round(activity.elevation_gain_m, 1),
        "avg_speed_mps": round(activity.avg_speed_mps, 3),
        "avg_hr_bpm": round(activity.avg_hr_bpm, 1) if activity.avg_hr_bpm is not None else None,
        "max_hr_bpm": activity.max_hr_bpm,
        "efficiency_kmh_per_bpm": round(efficiency, 3) if efficiency is not None else None,
        "headwind_kmh": _activity_wind(activity),
        "relative_score": 0.0,
    }


def add_relative_scores(metrics: list[dict[str, Any]]) -> None:
    speeds = [float(metric["avg_speed_mps"]) for metric in metrics if metric.get("avg_speed_mps") is not None]
    elevations = [float(metric["elevation_gain_m"]) for metric in metrics if metric.get("elevation_gain_m") is not None]
    efficiencies = [
        float(metric["efficiency_kmh_per_bpm"])
        for metric in metrics
        if metric.get("efficiency_kmh_per_bpm") is not None
    ]

    def normalized(value: float | None, values: list[float]) -> float:
        if value is None or not values:
            return 0.5
        low, high = min(values), max(values)
        return 0.5 if high == low else (value - low) / (high - low)

    for metric in metrics:
        speed = normalized(_number(metric.get("avg_speed_mps")), speeds)
        climbing = normalized(_number(metric.get("elevation_gain_m")), elevations)
        efficiency = normalized(_number(metric.get("efficiency_kmh_per_bpm")), efficiencies)
        metric["relative_score"] = round((speed * 0.45 + efficiency * 0.4 + climbing * 0.15) * 100, 1)


def normalized_profile(activity: Activity, maximum: int = 101) -> dict[str, Any]:
    points = activity.track_points or []
    if not points:
        return {"activity_id": activity.id, "title": activity.title, "points": []}
    maximum = max(2, maximum)
    total_distance = max((_number(point.get("distance_m")) or 0 for point in points), default=0)
    count = min(maximum, len(points))
    if total_distance > 0:
        selected_indexes: list[int] = []
        cursor = 0
        for sample_index in range(count):
            target = total_distance * sample_index / max(count - 1, 1)
            while cursor < len(points) - 1 and (_number(points[cursor].get("distance_m")) or 0) < target:
                cursor += 1
            candidates = [cursor]
            if cursor:
                candidates.append(cursor - 1)
            selected_indexes.append(
                min(candidates, key=lambda item: abs((_number(points[item].get("distance_m")) or 0) - target))
            )
        selected_indexes = sorted(set(selected_indexes))
    else:
        selected_indexes = sorted(
            set(round(index * (len(points) - 1) / max(count - 1, 1)) for index in range(count))
        )
    profile: list[dict[str, Any]] = []
    for index in selected_indexes:
        point = points[index]
        distance = _number(point.get("distance_m")) or 0
        progress = distance / total_distance * 100 if total_distance else index / max(len(points) - 1, 1) * 100
        speed = _number(point.get("speed_mps"))
        profile.append(
            {
                "progress_percent": round(progress, 1),
                "distance_km": round(distance / 1000, 2),
                "elevation_m": _number(point.get("altitude_m")),
                "speed_kmh": round(speed * 3.6, 1) if speed is not None else None,
                "heart_rate_bpm": point.get("heart_rate_bpm"),
            }
        )
    return {"activity_id": activity.id, "title": activity.title, "points": profile}


def segment_metrics(activity: Activity, start_km: float, end_km: float) -> dict[str, Any]:
    start_m, end_m = sorted((max(0.0, start_km * 1000), max(0.0, end_km * 1000)))
    selected = [
        (index, point)
        for index, point in enumerate(activity.track_points or [])
        if start_m <= (_number(point.get("distance_m")) or 0) <= end_m
    ]
    if len(selected) < 2:
        return {"error": "Für diesen Streckenabschnitt sind zu wenige Messpunkte vorhanden."}
    first_index, first = selected[0]
    last_index, last = selected[-1]
    distance = (_number(last.get("distance_m")) or end_m) - (_number(first.get("distance_m")) or start_m)
    try:
        started = datetime.fromisoformat(str(first["time"]).replace("Z", "+00:00"))
        ended = datetime.fromisoformat(str(last["time"]).replace("Z", "+00:00"))
        duration = max(0.0, (ended - started).total_seconds())
    except (KeyError, TypeError, ValueError):
        duration = 0.0
    speeds = [_number(point.get("speed_mps")) for _, point in selected]
    speed_values = [value for value in speeds if value is not None]
    heart_rates = [_number(point.get("heart_rate_bpm")) for _, point in selected]
    hr_values = [value for value in heart_rates if value is not None]
    altitudes = [_number(point.get("altitude_m")) for _, point in selected]
    altitude_values = [value for value in altitudes if value is not None]
    gain = loss = 0.0
    for previous, current in zip(altitude_values, altitude_values[1:]):
        delta = current - previous
        gain += max(delta, 0)
        loss += max(-delta, 0)
    elevation_delta = altitude_values[-1] - altitude_values[0] if len(altitude_values) >= 2 else 0.0
    moving_time = 0.0
    weighted_hr_sum = 0.0
    heart_rate_time = 0.0
    for (_, previous), (_, current) in zip(selected, selected[1:]):
        try:
            previous_time = datetime.fromisoformat(str(previous["time"]).replace("Z", "+00:00"))
            current_time = datetime.fromisoformat(str(current["time"]).replace("Z", "+00:00"))
            delta_seconds = (current_time - previous_time).total_seconds()
        except (KeyError, TypeError, ValueError):
            continue
        if not 0 < delta_seconds <= 300:
            continue
        previous_distance = _number(previous.get("distance_m")) or 0
        current_distance = _number(current.get("distance_m")) or previous_distance
        interval_speed = _number(current.get("speed_mps"))
        if interval_speed is None:
            interval_speed = max(0.0, current_distance - previous_distance) / delta_seconds
        if delta_seconds <= 120 and interval_speed >= 0.5:
            moving_time += delta_seconds
        previous_hr = _number(previous.get("heart_rate_bpm"))
        current_hr = _number(current.get("heart_rate_bpm"))
        if previous_hr is not None or current_hr is not None:
            interval_hr = mean(value for value in (previous_hr, current_hr) if value is not None)
            weighted_hr_sum += interval_hr * delta_seconds
            heart_rate_time += delta_seconds
    route_samples = (activity.weather or {}).get("route_weather_samples") or []
    wind_values = [
        (_number(sample.get("headwind_component_kmh")), _number(sample.get("weight_m")) or 1.0)
        for sample in route_samples
        if first_index <= int(sample.get("point_index", -1)) <= last_index
    ]
    valid_wind = [(value, weight) for value, weight in wind_values if value is not None]
    return {
        "activity_id": activity.id,
        "start_km": round(start_m / 1000, 2),
        "end_km": round(end_m / 1000, 2),
        "distance_km": round(distance / 1000, 2),
        "duration_s": round(duration),
        "moving_time_s": round(moving_time),
        "avg_speed_kmh": round(distance / moving_time * 3.6, 1) if moving_time else None,
        "max_speed_kmh": round(max(speed_values) * 3.6, 1) if speed_values else None,
        "avg_heart_rate_bpm": round(weighted_hr_sum / heart_rate_time) if heart_rate_time else None,
        "max_heart_rate_bpm": round(max(hr_values)) if hr_values else None,
        "elevation_gain_m": round(gain, 1),
        "elevation_loss_m": round(loss, 1),
        "average_grade_percent": round(elevation_delta / distance * 100, 1) if distance > 0 else None,
        "net_headwind_kmh": round(
            sum(value * weight for value, weight in valid_wind) / sum(weight for _, weight in valid_wind),
            1,
        ) if valid_wind else None,
    }


def coaching_context(activity: Activity, similar: list[Activity], goals: list[str]) -> dict[str, Any]:
    if not similar:
        return {"similar_activities": [], "development": {}, "training_goals": goals}
    avg_speed = mean(candidate.avg_speed_mps for candidate in similar)
    hr_candidates = [candidate.avg_hr_bpm for candidate in similar if candidate.avg_hr_bpm is not None]
    avg_hr = mean(hr_candidates) if hr_candidates else None
    distance_candidates = [candidate.distance_m for candidate in similar]
    target_speed_kmh = activity.avg_speed_mps * 3.6
    comparison_quality = "similar" if len(similar) >= 3 and all(
        similarity_score(activity, candidate) <= 1.5 for candidate in similar
    ) else "broad"
    return {
        "similar_activities": [
            {
                "id": candidate.id,
                "title": candidate.title,
                "date": candidate.started_at.date().isoformat(),
                "distance_km": round(candidate.distance_m / 1000, 1),
                "average_speed_kmh": round(candidate.avg_speed_mps * 3.6, 1),
                "average_heart_rate_bpm": round(candidate.avg_hr_bpm) if candidate.avg_hr_bpm else None,
                "elevation_gain_m": round(candidate.elevation_gain_m),
                "net_headwind_kmh": _activity_wind(candidate),
            }
            for candidate in similar
        ],
        "development": {
            "comparison_count": len(similar),
            "comparison_quality": comparison_quality,
            "average_comparison_distance_km": round(mean(distance_candidates) / 1000, 1),
            "speed_difference_kmh": round(target_speed_kmh - avg_speed * 3.6, 1),
            "heart_rate_difference_bpm": round(activity.avg_hr_bpm - avg_hr, 1)
            if activity.avg_hr_bpm is not None and avg_hr is not None
            else None,
        },
        "training_goals": goals,
    }
