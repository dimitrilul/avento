from __future__ import annotations

import calendar
import math
from collections import defaultdict
from datetime import date, timedelta
from statistics import median
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from .models import Activity


METRIC_KEYS = (
    "activity_count",
    "distance_m",
    "duration_s",
    "moving_time_s",
    "elevation_gain_m",
    "training_load",
    "avg_speed_mps",
    "avg_hr_bpm",
    "hydration_ml",
)


def choose_granularity(date_from: date, date_to: date, requested: str = "auto") -> str:
    if requested in {"day", "week", "month"}:
        return requested
    days = max(1, (date_to - date_from).days + 1)
    if days <= 45:
        return "day"
    if days <= 180:
        return "week"
    return "month"


def _bucket_start(value: date, granularity: str) -> date:
    if granularity == "week":
        return value - timedelta(days=value.weekday())
    if granularity == "month":
        return value.replace(day=1)
    return value


def _next_bucket(value: date, granularity: str) -> date:
    if granularity == "week":
        return value + timedelta(days=7)
    if granularity == "month":
        return (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return value + timedelta(days=1)


def totals(activities: Iterable[Activity]) -> dict[str, Any]:
    items = list(activities)
    distance = sum(activity.distance_m for activity in items)
    duration = sum(activity.duration_s for activity in items)
    moving = sum(activity.moving_time_s for activity in items)
    hr_weight = sum(activity.moving_time_s for activity in items if activity.avg_hr_bpm is not None)
    weighted_hr = sum(
        float(activity.avg_hr_bpm) * activity.moving_time_s
        for activity in items
        if activity.avg_hr_bpm is not None
    )
    return {
        "activity_count": len(items),
        "distance_m": round(distance, 2),
        "duration_s": round(duration, 2),
        "moving_time_s": round(moving, 2),
        "elevation_gain_m": round(sum(activity.elevation_gain_m for activity in items), 2),
        "training_load": round(sum(activity.training_load for activity in items), 2),
        "avg_speed_mps": round(distance / moving, 3) if moving else None,
        "avg_hr_bpm": round(weighted_hr / hr_weight, 1) if hr_weight else None,
        "hydration_ml": sum(activity.hydration_ml or 0 for activity in items),
        "hydration_activity_count": sum(activity.hydration_ml is not None for activity in items),
    }


def _series(
    activities: list[Activity],
    date_from: date,
    date_to: date,
    granularity: str,
    timezone_name: str,
) -> list[dict[str, Any]]:
    local_timezone = ZoneInfo(timezone_name)
    grouped: dict[date, list[Activity]] = defaultdict(list)
    for activity in activities:
        started_at = activity.started_at if activity.started_at.tzinfo else activity.started_at.replace(tzinfo=ZoneInfo("UTC"))
        grouped[_bucket_start(started_at.astimezone(local_timezone).date(), granularity)].append(activity)
    current = _bucket_start(date_from, granularity)
    end = _bucket_start(date_to, granularity)
    result: list[dict[str, Any]] = []
    bucket_count = 0
    while current <= end and bucket_count < 5_000:
        result.append({"period_start": current.isoformat(), **totals(grouped.get(current, []))})
        current = _next_bucket(current, granularity)
        bucket_count += 1
    return result


def _percent_change(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None or float(previous) == 0:
        return None
    return round((float(current) - float(previous)) / abs(float(previous)) * 100, 1)


def build_statistics(
    activities: list[Activity],
    previous_activities: list[Activity],
    date_from: date,
    date_to: date,
    previous_from: date,
    previous_to: date,
    requested_granularity: str = "auto",
    timezone_name: str = "UTC",
) -> dict[str, Any]:
    granularity = choose_granularity(date_from, date_to, requested_granularity)
    current_totals = totals(activities)
    previous_totals = totals(previous_activities)
    changes = {
        key: _percent_change(current_totals.get(key), previous_totals.get(key))
        for key in METRIC_KEYS
    }
    monthly: dict[str, list[Activity]] = defaultdict(list)
    local_timezone = ZoneInfo(timezone_name)
    for activity in activities:
        started_at = activity.started_at if activity.started_at.tzinfo else activity.started_at.replace(tzinfo=ZoneInfo("UTC"))
        monthly[started_at.astimezone(local_timezone).strftime("%Y-%m")].append(activity)
    by_month = [
        {"month": month, **totals(values)}
        for month, values in sorted(monthly.items())
    ]
    return {
        **current_totals,
        "granularity": granularity,
        "series": _series(activities, date_from, date_to, granularity, timezone_name),
        "comparison": {
            "date_from": previous_from.isoformat(),
            "date_to": previous_to.isoformat(),
            **previous_totals,
            "changes": changes,
        },
        "by_month": by_month,
    }


def _period_end(value: date, granularity: str) -> date:
    if granularity == "year":
        return date(value.year, 12, 31)
    return date(value.year, value.month, calendar.monthrange(value.year, value.month)[1])


def _next_period(value: date, granularity: str) -> date:
    if granularity == "year":
        return date(value.year + 1, 1, 1)
    return _next_bucket(value, "month")


def _period_aggregates(
    activities: list[Activity],
    date_from: date,
    date_to: date,
    granularity: str,
    timezone_name: str,
) -> list[dict[str, Any]]:
    timezone = ZoneInfo(timezone_name)
    grouped: dict[date, list[Activity]] = defaultdict(list)
    for activity in activities:
        started = activity.started_at if activity.started_at.tzinfo else activity.started_at.replace(tzinfo=ZoneInfo("UTC"))
        local_date = started.astimezone(timezone).date()
        key = date(local_date.year, 1, 1) if granularity == "year" else local_date.replace(day=1)
        grouped[key].append(activity)
    current = date(date_from.year, 1, 1) if granularity == "year" else date_from.replace(day=1)
    end = date(date_to.year, 1, 1) if granularity == "year" else date_to.replace(day=1)
    result: list[dict[str, Any]] = []
    previous_totals: dict[str, Any] | None = None
    while current <= end:
        aggregate = totals(grouped.get(current, []))
        changes = (
            {key: _percent_change(aggregate.get(key), previous_totals.get(key)) for key in METRIC_KEYS}
            if previous_totals is not None
            else {}
        )
        result.append(
            {
                "period": str(current.year) if granularity == "year" else current.strftime("%Y-%m"),
                "period_start": max(current, date_from),
                "period_end": min(_period_end(current, granularity), date_to),
                **aggregate,
                "changes_from_previous": changes,
            }
        )
        previous_totals = aggregate
        current = _next_period(current, granularity)
    return result


def _change_percent(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def _finite_number(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _median_metric(activities: list[Activity], metric) -> float | None:
    values = [float(value) for activity in activities if (value := metric(activity)) is not None and math.isfinite(float(value))]
    return median(values) if values else None


def _rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        rank = (cursor + end - 1) / 2 + 1
        for index, _ in indexed[cursor:end]:
            ranks[index] = rank
        cursor = end
    return ranks


def _spearman(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    x_ranks = _rank([pair[0] for pair in pairs])
    y_ranks = _rank([pair[1] for pair in pairs])
    x_mean = sum(x_ranks) / len(x_ranks)
    y_mean = sum(y_ranks) / len(y_ranks)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_ranks, y_ranks))
    denominator = math.sqrt(
        sum((x - x_mean) ** 2 for x in x_ranks) * sum((y - y_mean) ** 2 for y in y_ranks)
    )
    return numerator / denominator if denominator else None


def _association_pattern(
    pairs: list[tuple[float, float]],
    *,
    kind: str,
    x_label: str,
    y_label: str,
    unit: str,
) -> dict[str, Any] | None:
    if len(pairs) < 8:
        return None
    ordered = sorted(pairs)
    half = len(ordered) // 2
    low = ordered[:half]
    high = ordered[-half:]
    low_y = median(pair[1] for pair in low)
    high_y = median(pair[1] for pair in high)
    effect = _change_percent(high_y, low_y)
    correlation = _spearman(pairs)
    if effect is None or correlation is None or abs(effect) < 4 or abs(correlation) < 0.35:
        return None
    direction = "höher" if effect > 0 else "niedriger"
    return {
        "kind": kind,
        "confidence": "hoch" if len(pairs) >= 16 and abs(correlation) >= 0.5 else "mittel",
        "sample_size": len(pairs),
        "statement": (
            f"In diesen Fahrten war {y_label} bei höherem {x_label} im Median um "
            f"{abs(effect):.1f} % {direction}. Das ist eine beobachtete Verbindung, keine Ursache."
        ),
        "evidence": {
            "spearman_correlation": round(correlation, 3),
            "lower_group_median": round(low_y, 3),
            "upper_group_median": round(high_y, 3),
            "metric_unit": unit,
            "effect_percent": effect,
            "lower_group_size": len(low),
            "upper_group_size": len(high),
        },
        "method": "Spearman-Rangkorrelation plus robuster Medianvergleich zweier gleich großer Gruppen",
    }


def _fitness_trend(activities: list[Activity]) -> dict[str, Any]:
    ordered = sorted((activity for activity in activities if activity.avg_speed_mps > 0), key=lambda item: item.started_at)
    if len(ordered) < 6:
        return {
            "status": "insufficient_data",
            "confidence": "niedrig",
            "sample_size": len(ordered),
            "speed_change_percent": None,
            "heart_rate_efficiency_change_percent": None,
            "statement": "Für eine robuste Fitnessentwicklung sind mindestens sechs Fahrten erforderlich.",
        }
    group_size = max(3, len(ordered) // 3)
    early, late = ordered[:group_size], ordered[-group_size:]
    early_speed = _median_metric(early, lambda activity: activity.avg_speed_mps)
    late_speed = _median_metric(late, lambda activity: activity.avg_speed_mps)
    speed_change = _change_percent(late_speed, early_speed)
    early_efficiency = _median_metric(
        early,
        lambda activity: activity.avg_speed_mps * 3.6 / activity.avg_hr_bpm if activity.avg_hr_bpm else None,
    )
    late_efficiency = _median_metric(
        late,
        lambda activity: activity.avg_speed_mps * 3.6 / activity.avg_hr_bpm if activity.avg_hr_bpm else None,
    )
    efficiency_change = _change_percent(late_efficiency, early_efficiency)
    signal = efficiency_change if efficiency_change is not None else speed_change
    if signal is not None and signal >= 4:
        status = "positive"
        wording = "Die jüngsten Fahrten zeigen in den verfügbaren Messwerten einen positiven Trend."
    elif signal is not None and signal <= -4:
        status = "negative"
        wording = "Die jüngsten Fahrten liegen in den verfügbaren Messwerten unter dem früheren Vergleichsniveau."
    else:
        status = "stable"
        wording = "Die verfügbaren Tempo- und Herzfrequenzwerte zeigen einen weitgehend stabilen Verlauf."
    return {
        "status": status,
        "confidence": "hoch" if len(ordered) >= 18 else "mittel",
        "sample_size": len(ordered),
        "speed_change_percent": speed_change,
        "heart_rate_efficiency_change_percent": efficiency_change,
        "statement": wording + " Unterschiedliche Strecken und Bedingungen begrenzen den Vergleich.",
    }


def _recovery_pattern(activities: list[Activity]) -> dict[str, Any] | None:
    ordered = sorted(activities, key=lambda activity: activity.started_at)
    entries: list[tuple[float, Activity]] = []
    for previous, current in zip(ordered, ordered[1:]):
        current_start = current.started_at if current.started_at.tzinfo else current.started_at.replace(tzinfo=ZoneInfo("UTC"))
        previous_end = previous.ended_at if previous.ended_at.tzinfo else previous.ended_at.replace(tzinfo=ZoneInfo("UTC"))
        gap_hours = (current_start - previous_end).total_seconds() / 3600
        if gap_hours >= 0:
            entries.append((gap_hours, current))

    def efficiency(activity: Activity) -> float | None:
        return activity.avg_speed_mps * 3.6 / activity.avg_hr_bpm if activity.avg_hr_bpm and activity.avg_speed_mps > 0 else None

    short_efficiency = [efficiency(activity) for gap, activity in entries if gap <= 36 and efficiency(activity) is not None]
    long_efficiency = [efficiency(activity) for gap, activity in entries if gap >= 60 and efficiency(activity) is not None]
    metric = "Tempo pro durchschnittlichem Herzschlag"
    unit = "km/h pro bpm"
    if len(short_efficiency) < 3 or len(long_efficiency) < 3:
        short_efficiency = [activity.avg_speed_mps for gap, activity in entries if gap <= 36 and activity.avg_speed_mps > 0]
        long_efficiency = [activity.avg_speed_mps for gap, activity in entries if gap >= 60 and activity.avg_speed_mps > 0]
        metric = "Durchschnittstempo"
        unit = "m/s"
    if len(short_efficiency) < 3 or len(long_efficiency) < 3:
        return None
    short_value = median(short_efficiency)
    long_value = median(long_efficiency)
    effect = _change_percent(long_value, short_value)
    if effect is None or abs(effect) < 4:
        return None
    direction = "höher" if effect > 0 else "niedriger"
    return {
        "kind": "recovery_spacing",
        "confidence": "mittel",
        "sample_size": len(short_efficiency) + len(long_efficiency),
        "statement": (
            f"Nach mindestens 60 Stunden Abstand war {metric} im Median um {abs(effect):.1f} % {direction} "
            "als nach höchstens 36 Stunden. Das beschreibt nur deine aufgezeichneten Fahrten und ist keine medizinische Aussage."
        ),
        "evidence": {
            "short_gap_hours_max": 36,
            "long_gap_hours_min": 60,
            "short_gap_median": round(short_value, 3),
            "long_gap_median": round(long_value, 3),
            "metric_unit": unit,
            "effect_percent": effect,
            "short_gap_sample_size": len(short_efficiency),
            "long_gap_sample_size": len(long_efficiency),
        },
        "method": "Medianvergleich von Fahrten nach kurzen und längeren Aktivitätsabständen",
    }


def build_long_term_insights(
    activities: list[Activity],
    previous_activities: list[Activity],
    date_from: date,
    date_to: date,
    previous_from: date,
    previous_to: date,
    timezone_name: str,
) -> dict[str, Any]:
    current = totals(activities)
    previous = totals(previous_activities)
    changes = {key: _percent_change(current.get(key), previous.get(key)) for key in METRIC_KEYS}
    patterns: list[dict[str, Any]] = []
    temperature_pairs = [
        (temperature, activity.avg_speed_mps)
        for activity in activities
        if activity.weather
        and (temperature := _finite_number(activity.weather.get("temperature_c"))) is not None
        and activity.avg_speed_mps > 0
        and math.isfinite(activity.avg_speed_mps)
    ]
    temperature = _association_pattern(
        temperature_pairs,
        kind="weather_temperature_pace",
        x_label="Temperaturniveau",
        y_label="das Durchschnittstempo",
        unit="m/s",
    )
    if temperature:
        patterns.append(temperature)
    wind_pairs = [
        (headwind, activity.avg_speed_mps)
        for activity in activities
        if (route_wind := (activity.weather or {}).get("route_wind"))
        and (headwind := _finite_number(route_wind.get("net_headwind_kmh"))) is not None
        and activity.avg_speed_mps > 0
        and math.isfinite(activity.avg_speed_mps)
    ]
    wind = _association_pattern(
        wind_pairs,
        kind="weather_wind_pace",
        x_label="der Gegenwindkomponente",
        y_label="das Durchschnittstempo",
        unit="m/s",
    )
    if wind:
        patterns.append(wind)
    recovery = _recovery_pattern(activities)
    if recovery:
        patterns.append(recovery)
    trend = _fitness_trend(activities)
    if trend["heart_rate_efficiency_change_percent"] is not None and abs(trend["heart_rate_efficiency_change_percent"]) >= 4:
        patterns.append(
            {
                "kind": "heart_rate_pace_development",
                "confidence": trend["confidence"],
                "sample_size": trend["sample_size"],
                "statement": (
                    "Das robuste Verhältnis aus Durchschnittstempo und mittlerer Herzfrequenz änderte sich zwischen "
                    f"frühem und spätem Drittel um {trend['heart_rate_efficiency_change_percent']:+.1f} %. "
                    "Das ist ein Trainingsdaten-Trend und keine medizinische Bewertung."
                ),
                "evidence": {
                    "change_percent": trend["heart_rate_efficiency_change_percent"],
                    "metric": "average_speed_kmh_per_average_heart_rate_bpm",
                },
                "method": "Medianvergleich des ersten und letzten Drittels in chronologischer Reihenfolge",
            }
        )
    return {
        "period": {"date_from": date_from, "date_to": date_to},
        "current": current,
        "previous_period": {"date_from": previous_from, "date_to": previous_to},
        "previous": previous,
        "changes": changes,
        "monthly": _period_aggregates(activities, date_from, date_to, "month", timezone_name),
        "yearly": _period_aggregates(activities, date_from, date_to, "year", timezone_name),
        "fitness_trend": trend,
        "patterns": patterns,
    }
