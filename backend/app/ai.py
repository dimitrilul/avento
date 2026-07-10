from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from .config import Settings
from .models import Activity


class SummaryProvider(ABC):
    name: str

    @abstractmethod
    def summarize(self, activity: Activity) -> str:
        raise NotImplementedError


def _hours(seconds: float) -> str:
    total_minutes = round(seconds / 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


def _activity_facts(activity: Activity) -> dict[str, Any]:
    weather = activity.weather or None
    if weather:
        weather = {
            key: round(value, 1) if isinstance(value, float) else value
            for key, value in weather.items()
        }
    return {
        "title": activity.title,
        "type": activity.activity_type,
        "start": activity.started_at.isoformat(),
        "distance_km": round(activity.distance_m / 1000, 1),
        "duration": _hours(activity.duration_s),
        "moving_duration": _hours(activity.moving_time_s),
        "elevation_gain_m": round(activity.elevation_gain_m),
        "average_speed_kmh": round(activity.avg_speed_mps * 3.6, 1),
        "maximum_speed_kmh": round(activity.max_speed_mps * 3.6, 1),
        "average_heart_rate_bpm": round(activity.avg_hr_bpm) if activity.avg_hr_bpm is not None else None,
        "maximum_heart_rate_bpm": activity.max_hr_bpm,
        "heart_rate_zone_seconds": activity.hr_zone_seconds,
        "weather": weather,
    }


class LocalSummaryProvider(SummaryProvider):
    name = "local"

    def summarize(self, activity: Activity) -> str:
        facts = _activity_facts(activity)
        opening = (
            f"{facts['title']}: {facts['distance_km']:.1f} km in {facts['duration']} "
            f"mit durchschnittlich {facts['average_speed_kmh']:.1f} km/h und "
            f"{facts['elevation_gain_m']} Höhenmetern."
        )
        details: list[str] = []
        if activity.avg_hr_bpm is not None:
            details.append(
                f"Die Herzfrequenz lag im Mittel bei {round(activity.avg_hr_bpm)} bpm"
                + (f" und maximal bei {activity.max_hr_bpm} bpm." if activity.max_hr_bpm else ".")
            )
        if activity.pause_time_s >= 60:
            details.append(f"Die erfasste Pausenzeit betrug {_hours(activity.pause_time_s)}.")
        if activity.weather and activity.weather.get("temperature_c") is not None:
            details.append(f"Zum Start wurden {activity.weather['temperature_c']} °C gemessen.")
        if not details:
            details.append("Für eine genauere Belastungseinordnung fehlen Herzfrequenz- oder Wetterdaten.")
        return " ".join([opening, *details])


class OpenAISummaryProvider(SummaryProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.model = settings.openai_model
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )

    def summarize(self, activity: Activity) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "Du bist ein sachlicher deutschsprachiger Radsport-Coach. Fasse die Aktivität in 3 bis 5 "
                "kurzen Sätzen zusammen. Nenne nur Werte aus den Daten, vermeide medizinische Aussagen und "
                "kennzeichne fehlende Sensorwerte nicht als null. Runde Herzfrequenz und Höhenmeter auf ganze "
                "Zahlen und alle anderen Dezimalwerte auf höchstens eine Nachkommastelle. Erwähne keine "
                "Trainingsbelastung, da dieser Wert ohne persönliche Kalibrierung nicht aussagekräftig ist."
            ),
            input=f"Aktivitätsdaten: {_activity_facts(activity)}",
            max_output_tokens=400,
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("Der KI-Provider hat keinen Text geliefert.")
        return text


def get_summary_provider(settings: Settings) -> SummaryProvider:
    if settings.openai_api_key:
        return OpenAISummaryProvider(settings)
    return LocalSummaryProvider()
