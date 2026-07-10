from __future__ import annotations

import json
import math
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import weather_facts
from ..analysis import (
    coaching_context,
    comparison_metric,
    find_similar_activities,
    normalized_profile,
    segment_metrics,
)
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, User
from ..schemas import ChatRequest, ChatResponse, ChatSource
from ..statistics import totals


router = APIRouter(prefix="/chat", tags=["Avento Coach"])


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_activities",
        "description": "Sucht Fahrten nach Zeitraum, Distanz und Typ und liefert kompakte Trainingswerte.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_from": {"type": ["string", "null"], "description": "Startdatum YYYY-MM-DD"},
                "date_to": {"type": ["string", "null"], "description": "Enddatum YYYY-MM-DD"},
                "min_distance_km": {"type": ["number", "null"]},
                "max_distance_km": {"type": ["number", "null"]},
                "activity_type": {"type": ["string", "null"]},
                "sort": {
                    "type": "string",
                    "enum": ["newest", "oldest", "distance_desc", "speed_desc", "duration_desc", "elevation_desc"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["date_from", "date_to", "min_distance_km", "max_distance_km", "activity_type", "sort", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "find_best_activities",
        "description": "Durchsucht die gesamte Trainingshistorie und rangiert die besten Fahrten nach einem Zielkriterium.",
        "parameters": {
            "type": "object",
            "properties": {
                "criterion": {
                    "type": "string",
                    "enum": ["endurance", "speed", "efficiency", "headwind_speed", "climbing", "longest", "training_load"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["criterion", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_activity_details",
        "description": "Lädt alle zusammengefassten Sensor-, Zonen- und Wetterwerte einer bestimmten Aktivität.",
        "parameters": {
            "type": "object",
            "properties": {"activity_id": {"type": "string"}},
            "required": ["activity_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "find_similar_activities",
        "description": "Findet frühere Fahrten mit ähnlicher Distanz, Dauer, Höhe, Typ und Startregion.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 3, "maximum": 10},
            },
            "required": ["activity_id", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_activities",
        "description": "Vergleicht zwei bis zehn konkrete Aktivitäten einschließlich Effizienz und Wind.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 10}
            },
            "required": ["activity_ids"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_training_statistics",
        "description": "Berechnet aggregierte Trainingswerte für einen Zeitraum.",
        "parameters": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Startdatum YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "Enddatum YYYY-MM-DD"},
            },
            "required": ["date_from", "date_to"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analyze_route_segment",
        "description": "Analysiert einen Kilometerabschnitt einer Aktivität mit Tempo, Puls, Höhe, Steigung und Wind.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "string"},
                "start_km": {"type": "number", "minimum": 0},
                "end_km": {"type": "number", "minimum": 0},
            },
            "required": ["activity_id", "start_km", "end_km"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_activity_track_analysis",
        "description": "Lädt ein kompaktes Höhen-, Tempo- und Herzfrequenzprofil sowie Kilometer-Splits einer Aktivität.",
        "parameters": {
            "type": "object",
            "properties": {
                "activity_id": {"type": "string"},
                "start_km": {"type": ["number", "null"], "minimum": 0},
                "end_km": {"type": ["number", "null"], "minimum": 0},
            },
            "required": ["activity_id", "start_km", "end_km"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def _activity(db: Session, user: User, activity_id: str) -> Activity | None:
    return db.scalar(select(Activity).where(Activity.user_id == user.id, Activity.id == activity_id))


def _compact(activity: Activity) -> dict[str, Any]:
    metric = comparison_metric(activity)
    return {
        **metric,
        "started_at": activity.started_at.isoformat(),
        "type": activity.activity_type,
        "max_speed_kmh": round(activity.max_speed_mps * 3.6, 1),
        "heart_rate_zones_seconds": activity.hr_zone_seconds or {},
        "weather": weather_facts(activity.weather),
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _local_midnight(value: date) -> datetime:
    timezone_name = get_settings().timezone
    return datetime.combine(value, time.min, tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)


def _execute_tool(
    name: str,
    arguments: dict[str, Any],
    db: Session,
    user: User,
    sources: dict[str, Activity],
) -> Any:
    if name == "search_activities":
        conditions: list[Any] = [Activity.user_id == user.id]
        date_from = _parse_date(arguments.get("date_from"))
        date_to = _parse_date(arguments.get("date_to"))
        if date_from and date_from < date(1900, 1, 1):
            return {"error": "Zeiträume vor 1900 werden nicht unterstützt."}
        if date_from and date_to and date_to < date_from:
            return {"error": "Das Enddatum muss am oder nach dem Startdatum liegen."}
        if date_from:
            conditions.append(Activity.started_at >= _local_midnight(date_from))
        if date_to:
            if date_to.year >= 9999:
                return {"error": "Das Enddatum liegt außerhalb des unterstützten Bereichs."}
            conditions.append(Activity.started_at < _local_midnight(date_to + timedelta(days=1)))
        if arguments.get("min_distance_km") is not None:
            conditions.append(Activity.distance_m >= float(arguments["min_distance_km"]) * 1000)
        if arguments.get("max_distance_km") is not None:
            conditions.append(Activity.distance_m <= float(arguments["max_distance_km"]) * 1000)
        if arguments.get("activity_type"):
            conditions.append(Activity.activity_type == str(arguments["activity_type"]).lower())
        limit = max(1, min(int(arguments.get("limit") or 10), 50))
        ordering = {
            "oldest": Activity.started_at.asc(),
            "distance_desc": Activity.distance_m.desc(),
            "speed_desc": Activity.avg_speed_mps.desc(),
            "duration_desc": Activity.moving_time_s.desc(),
            "elevation_desc": Activity.elevation_gain_m.desc(),
        }.get(str(arguments.get("sort")), Activity.started_at.desc())
        activities = db.scalars(
            select(Activity).where(*conditions).order_by(ordering).limit(limit)
        ).all()
        sources.update({activity.id: activity for activity in activities})
        return [_compact(activity) for activity in activities]
    if name == "find_best_activities":
        activities = db.scalars(select(Activity).where(Activity.user_id == user.id)).all()
        criterion = str(arguments.get("criterion") or "endurance")

        def rank(activity: Activity) -> float:
            metric = comparison_metric(activity)
            if criterion == "speed":
                return activity.avg_speed_mps
            if criterion == "efficiency":
                return float(metric.get("efficiency_kmh_per_bpm") or 0)
            if criterion == "headwind_speed":
                headwind = float(metric.get("headwind_kmh") or 0)
                return activity.avg_speed_mps if headwind >= 1 else -1
            if criterion == "climbing":
                return activity.elevation_gain_m
            if criterion == "longest":
                return activity.distance_m
            if criterion == "training_load":
                return activity.training_load
            heart_rate_factor = max(float(activity.avg_hr_bpm or 150), 1)
            return activity.moving_time_s * activity.avg_speed_mps / heart_rate_factor

        ranked = sorted(activities, key=rank, reverse=True)
        if criterion == "headwind_speed":
            ranked = [activity for activity in ranked if rank(activity) >= 0]
        limit = max(1, min(int(arguments.get("limit") or 5), 10))
        ranked = ranked[:limit]
        sources.update({activity.id: activity for activity in ranked})
        return {"criterion": criterion, "activities": [_compact(activity) for activity in ranked]}
    if name == "get_activity_details":
        activity = _activity(db, user, str(arguments.get("activity_id")))
        if not activity:
            return {"error": "Aktivität nicht gefunden."}
        sources[activity.id] = activity
        return _compact(activity)
    if name == "find_similar_activities":
        activity = _activity(db, user, str(arguments.get("activity_id")))
        if not activity:
            return {"error": "Aktivität nicht gefunden."}
        candidates = db.scalars(
            select(Activity)
            .where(Activity.user_id == user.id, Activity.id != activity.id, Activity.started_at < activity.started_at)
            .order_by(Activity.started_at.desc())
            .limit(50)
        ).all()
        similar = find_similar_activities(activity, candidates, int(arguments.get("limit") or 7))
        sources[activity.id] = activity
        sources.update({candidate.id: candidate for candidate in similar})
        return coaching_context(activity, similar, user.training_goals or [])
    if name == "compare_activities":
        ids = list(dict.fromkeys(str(value) for value in arguments.get("activity_ids") or []))[:10]
        activities = db.scalars(
            select(Activity).where(Activity.user_id == user.id, Activity.id.in_(ids))
        ).all()
        by_id = {activity.id: activity for activity in activities}
        ordered = [by_id[activity_id] for activity_id in ids if activity_id in by_id]
        sources.update({activity.id: activity for activity in ordered})
        return [_compact(activity) for activity in ordered]
    if name == "get_training_statistics":
        date_from = _parse_date(arguments.get("date_from"))
        date_to = _parse_date(arguments.get("date_to"))
        if not date_from or not date_to:
            return {"error": "Ungültiger Zeitraum."}
        if date_to < date_from or date_from < date(1900, 1, 1) or date_to.year >= 9999:
            return {"error": "Der Zeitraum liegt außerhalb des unterstützten Bereichs."}
        activities = db.scalars(
            select(Activity).where(
                Activity.user_id == user.id,
                Activity.started_at >= _local_midnight(date_from),
                Activity.started_at < _local_midnight(date_to + timedelta(days=1)),
            )
        ).all()
        sources.update({activity.id: activity for activity in activities[:10]})
        return {"date_from": date_from.isoformat(), "date_to": date_to.isoformat(), **totals(activities)}
    if name == "analyze_route_segment":
        activity = _activity(db, user, str(arguments.get("activity_id")))
        if not activity:
            return {"error": "Aktivität nicht gefunden."}
        sources[activity.id] = activity
        return segment_metrics(activity, float(arguments.get("start_km") or 0), float(arguments.get("end_km") or 0))
    if name == "get_activity_track_analysis":
        activity = _activity(db, user, str(arguments.get("activity_id")))
        if not activity:
            return {"error": "Aktivität nicht gefunden."}
        sources[activity.id] = activity
        profile = normalized_profile(activity, maximum=101)
        total_splits = max(1, int(math.ceil(activity.distance_m / 1000)))
        requested_start = max(0, int(math.floor(float(arguments.get("start_km") or 0))))
        requested_end = int(math.ceil(float(arguments.get("end_km") or total_splits)))
        split_end = min(total_splits, requested_end, requested_start + 60)
        splits = [
            segment_metrics(activity, float(kilometre), min(float(kilometre + 1), activity.distance_m / 1000))
            for kilometre in range(requested_start, split_end)
            if kilometre * 1000 < activity.distance_m
        ]
        return {
            "activity_id": activity.id,
            "profile": profile["points"],
            "kilometer_splits": splits,
            "returned_range_km": [requested_start, split_end],
            "has_more_splits": split_end < total_splits,
        }
    return {"error": "Unbekanntes Werkzeug."}


def _local_answer(payload: ChatRequest, db: Session, user: User) -> tuple[str, list[Activity], list[str]]:
    activities = db.scalars(
        select(Activity).where(Activity.user_id == user.id).order_by(Activity.started_at.desc())
    ).all()
    if not activities:
        return "Importiere zuerst eine Aktivität, damit ich deine Entwicklung analysieren kann.", [], ["search_activities"]
    selected = _activity(db, user, payload.activity_id) if payload.activity_id else None
    message = payload.message.lower()
    if selected:
        earlier = [activity for activity in activities if activity.started_at < selected.started_at]
        similar = find_similar_activities(selected, earlier, 7)
        context = coaching_context(selected, similar, user.training_goals or [])
        development = context.get("development") or {}
        speed = development.get("speed_difference_kmh")
        heart_rate = development.get("heart_rate_difference_bpm")
        quality = development.get("comparison_quality")
        answer = f"{selected.title}: {selected.distance_m / 1000:.1f} km mit {selected.avg_speed_mps * 3.6:.1f} km/h im Durchschnitt."
        if speed is not None:
            basis = "ähnlichen früheren Fahrten" if quality == "similar" else "früheren Fahrten mit eingeschränkter Vergleichbarkeit"
            answer += f" Gegenüber {len(similar)} {basis} liegt das Tempo bei {speed:+.1f} km/h"
            if heart_rate is not None:
                answer += f" und die durchschnittliche Herzfrequenz bei {heart_rate:+.0f} bpm"
            answer += "."
        return answer, [selected, *similar], ["get_activity_details", "find_similar_activities"]
    if "gegenwind" in message or "rückenwind" in message or "wind" in message:
        wants_tailwind = "rückenwind" in message and "gegenwind" not in message
        with_wind = [
            activity
            for activity in activities
            if (
                float(comparison_metric(activity).get("headwind_kmh") or 0) <= -1
                if wants_tailwind
                else float(comparison_metric(activity).get("headwind_kmh") or 0) >= 1
            )
        ]
        if with_wind:
            fastest = max(with_wind, key=lambda activity: activity.avg_speed_mps)
            wind = comparison_metric(fastest).get("headwind_kmh")
            wind_label = "Rückenwindkomponente" if wants_tailwind else "Gegenwindkomponente"
            return (
                f"Unter den Fahrten mit passender streckenbezogener Windlage war „{fastest.title}“ mit "
                f"{fastest.avg_speed_mps * 3.6:.1f} km/h am schnellsten; die mittlere {wind_label} lag bei {abs(float(wind)):.1f} km/h.",
                [fastest],
                ["search_activities", "compare_activities"],
            )
    if "fitness" in message or "entwick" in message or "ausdauer" in message:
        chronological = list(reversed(activities[:10]))
        midpoint = max(1, len(chronological) // 2)
        earlier, recent = chronological[:midpoint], chronological[midpoint:]
        if recent and earlier:
            recent_speed = mean(activity.avg_speed_mps for activity in recent) * 3.6
            earlier_speed = mean(activity.avg_speed_mps for activity in earlier) * 3.6
            return (
                f"Über deine letzten {len(chronological)} Fahrten stieg das mittlere Tempo in der jüngeren Hälfte "
                f"um {recent_speed - earlier_speed:+.1f} km/h. Für eine belastbarere Ausdaueraussage vergleiche ich "
                "zusätzlich ähnliche Distanzen, Höhenprofile und Herzfrequenzen, sobald mehr Fahrten vorliegen.",
                chronological,
                ["search_activities", "get_training_statistics"],
            )
    best = max(
        activities,
        key=lambda activity: (activity.moving_time_s / 3600) * (activity.avg_speed_mps * 3.6) / max(activity.avg_hr_bpm or 150, 1),
    )
    return (
        f"Eine besonders starke Ausdauereinheit ist „{best.title}“: {best.distance_m / 1000:.1f} km in "
        f"{best.moving_time_s / 3600:.1f} Stunden bei {best.avg_speed_mps * 3.6:.1f} km/h"
        + (f" und durchschnittlich {best.avg_hr_bpm:.0f} bpm." if best.avg_hr_bpm else "."),
        [best],
        ["search_activities", "compare_activities"],
    )


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        answer, activities, tools_used = _local_answer(payload, db, current_user)
        return ChatResponse(
            answer=answer,
            provider="local",
            sources=[
                ChatSource(activity_id=activity.id, title=activity.title, started_at=activity.started_at)
                for activity in list({activity.id: activity for activity in activities}.values())[:10]
            ],
            tools_used=tools_used,
        )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.ai_timeout_seconds,
        max_retries=1,
    )
    focus_activity = _activity(db, current_user, payload.activity_id) if payload.activity_id else None
    user_content = payload.message
    if focus_activity:
        user_content += (
            f"\n\nIn der Oberfläche ist die Fokusfahrt „{focus_activity.title}“ "
            f"(activity_id: {focus_activity.id}) ausgewählt. Rufe ihre Details ab und beziehe die Antwort konkret darauf."
        )
    input_items: list[Any] = [
        {"role": message.role, "content": message.content}
        for message in payload.history[-12:]
    ]
    input_items.append({"role": "user", "content": user_content})
    sources: dict[str, Activity] = {focus_activity.id: focus_activity} if focus_activity else {}
    tools_used: list[str] = []
    instructions = (
        "Du bist Avento Coach, ein persönlicher deutschsprachiger Radsport-Coach. Nutze die Werkzeuge gezielt, "
        "statt Trainingswerte zu erraten. Vergleiche bevorzugt 3 bis 10 ähnliche frühere Fahrten und berücksichtige "
        "Distanz, Dauer, Höhenprofil, Herzfrequenz und streckenbezogenen Wind. Erkenne Fortschritte, lobe konkrete "
        "Leistungen, motiviere unaufdringlich und gib höchstens zwei umsetzbare Trainingshinweise. Trenne belegte "
        "Werte klar von plausiblen Erklärungen. Gib keine medizinischen Diagnosen. Antworte kompakt und nenne die "
        "Titel verwendeter Aktivitäten. Nutze für Superlative wie beste, schnellste oder längste Fahrt das Werkzeug "
        "find_best_activities, das die gesamte Historie durchsucht. Nutze für Kilometerwerte und Höhenprofile "
        "get_activity_track_analysis. Wenn Vergleichsdaten nur breit vergleichbar sind, leite daraus keinen "
        "Fitnessfortschritt ab."
    )
    try:
        response = client.responses.create(
            model=settings.openai_model,
            instructions=instructions,
            tools=TOOLS,
            input=input_items,
            max_output_tokens=750,
            store=False,
            include=["reasoning.encrypted_content"],
        )
        executed_tool_calls = 0
        for _ in range(4):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break
            input_items += response.output
            for call in calls:
                if executed_tool_calls >= 12:
                    result = {"error": "Das Werkzeuglimit dieser Anfrage ist erreicht."}
                else:
                    try:
                        arguments = json.loads(call.arguments)
                    except (TypeError, json.JSONDecodeError):
                        arguments = {}
                    result = _execute_tool(call.name, arguments, db, current_user, sources)
                    tools_used.append(call.name)
                    executed_tool_calls += 1
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
            response = client.responses.create(
                model=settings.openai_model,
                instructions=instructions,
                tools=TOOLS,
                input=input_items,
                max_output_tokens=750,
                store=False,
                include=["reasoning.encrypted_content"],
            )
        answer = response.output_text.strip()
        if not answer:
            raise RuntimeError("Leere KI-Antwort")
        return ChatResponse(
            answer=answer,
            provider="openai",
            sources=[
                ChatSource(activity_id=activity.id, title=activity.title, started_at=activity.started_at)
                for activity in list(sources.values())[:10]
            ],
            tools_used=list(dict.fromkeys(tools_used)),
        )
    except Exception:
        answer, activities, local_tools = _local_answer(payload, db, current_user)
        return ChatResponse(
            answer=answer,
            provider="local_fallback",
            sources=[
                ChatSource(activity_id=activity.id, title=activity.title, started_at=activity.started_at)
                for activity in list({activity.id: activity for activity in activities}.values())[:10]
            ],
            tools_used=list(dict.fromkeys([*tools_used, *local_tools])),
        )
