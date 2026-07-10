from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from .config import Settings
from .models import Activity


class SummaryProvider(ABC):
    name: str

    @abstractmethod
    def summarize(self, activity: Activity, coaching: dict[str, Any] | None = None) -> str:
        raise NotImplementedError


def _hours(seconds: float) -> str:
    total_minutes = round(seconds / 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


def weather_facts(weather: dict[str, Any] | None) -> dict[str, Any] | None:
    if not weather:
        return None
    allowed = {
        "provider",
        "observed_at",
        "temperature_c",
        "apparent_temperature_c",
        "precipitation_mm",
        "weather_code",
        "wind_speed_kmh",
        "wind_direction_deg",
        "humidity_percent",
    }
    result = {
        key: round(value, 1) if isinstance(value, float) else value
        for key, value in weather.items()
        if key in allowed
    }
    route_wind = weather.get("route_wind")
    if isinstance(route_wind, dict):
        result["route_wind"] = {
            key: round(value, 1) if isinstance(value, float) else value
            for key, value in route_wind.items()
            if key != "samples"
        }
    return result


def _activity_facts(activity: Activity) -> dict[str, Any]:
    weather = weather_facts(activity.weather)
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

    def summarize(self, activity: Activity, coaching: dict[str, Any] | None = None) -> str:
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
        route_wind = (activity.weather or {}).get("route_wind") or {}
        net_headwind = route_wind.get("net_headwind_kmh")
        if isinstance(net_headwind, (int, float)):
            if net_headwind >= 1.5:
                details.append(f"Im Streckenverlauf wirkten im Mittel etwa {net_headwind:.1f} km/h Gegenwindkomponente.")
            elif net_headwind <= -1.5:
                details.append(f"Die Strecke profitierte im Mittel von etwa {abs(net_headwind):.1f} km/h Rückenwindkomponente.")
        development = (coaching or {}).get("development") or {}
        comparison_count = int(development.get("comparison_count") or 0)
        comparison_quality = development.get("comparison_quality")
        speed_difference = development.get("speed_difference_kmh")
        heart_rate_difference = development.get("heart_rate_difference_bpm")
        if comparison_count and isinstance(speed_difference, (int, float)):
            direction = "höher" if speed_difference >= 0 else "niedriger"
            basis = (
                f"{comparison_count} ähnlichen früheren Fahrten"
                if comparison_quality == "similar"
                else f"{comparison_count} früheren Fahrten mit eingeschränkter Vergleichbarkeit"
            )
            comparison = (
                f"Gegenüber {basis} war dein Durchschnittstempo "
                f"um {abs(speed_difference):.1f} km/h {direction}"
            )
            if isinstance(heart_rate_difference, (int, float)):
                pulse_direction = "höher" if heart_rate_difference >= 0 else "niedriger"
                comparison += f", bei einer um {abs(heart_rate_difference):.0f} bpm {pulse_direction}en Herzfrequenz."
            else:
                comparison += "."
            details.append(comparison)
            if comparison_quality == "similar" and speed_difference > 0.4 and (not isinstance(heart_rate_difference, (int, float)) or heart_rate_difference <= 2):
                details.append("Das ist ein starkes Zeichen für verbesserte Ausdauer und Effizienz – weiter so!")
            elif comparison_quality == "similar" and speed_difference >= 0:
                details.append("Solide Entwicklung: Die Einheit passt gut zu einem kontrollierten Ausdaueraufbau.")
            elif comparison_quality != "similar":
                details.append("Für eine belastbare Entwicklungsbewertung braucht es noch mehr wirklich vergleichbare Fahrten.")
            else:
                details.append("Ein ruhigerer Tag ist kein Rückschritt; nutze die Einheit als belastbaren Trainingsbaustein.")
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

    def summarize(self, activity: Activity, coaching: dict[str, Any] | None = None) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "Du bist ein aufmerksamer, motivierender deutschsprachiger Radsport-Coach. Analysiere die "
                "Aktivität in 4 bis 7 kurzen Sätzen. Vergleiche sie mit den bereitgestellten ähnlichen früheren "
                "Fahrten, erkenne Ausdauer- und Effizienzfortschritte, lobe konkrete gute Leistungen und gib "
                "höchstens einen realistischen Trainingshinweis. Interpretiere Temperatur, Niederschlag sowie "
                "Gegen-, Rücken- und Seitenwind nur, wenn Daten vorliegen. Nenne nur Werte aus den Daten, "
                "vermeide medizinische Aussagen und "
                "kennzeichne fehlende Sensorwerte nicht als null. Runde Herzfrequenz und Höhenmeter auf ganze "
                "Zahlen und alle anderen Dezimalwerte auf höchstens eine Nachkommastelle. Erwähne keine "
                "Trainingsbelastung, da dieser Wert ohne persönliche Kalibrierung nicht aussagekräftig ist. "
                "Formuliere Unterschiede immer mit Vergleichsbasis und stelle Vermutungen klar als solche dar. "
                "Wenn comparison_quality 'broad' ist, bezeichne die Fahrten nicht als ähnlich und leite daraus "
                "keinen Fitnessfortschritt ab."
            ),
            input=f"Aktivitätsdaten: {_activity_facts(activity)}\nCoaching-Kontext: {coaching or {}}",
            max_output_tokens=650,
            store=False,
        )
        text = response.output_text.strip()
        if not text:
            raise RuntimeError("Der KI-Provider hat keinen Text geliefert.")
        return text


def get_summary_provider(settings: Settings) -> SummaryProvider:
    if settings.openai_api_key:
        return OpenAISummaryProvider(settings)
    return LocalSummaryProvider()


def comparison_summary(
    settings: Settings,
    activities: list[Activity],
    metrics: list[dict[str, Any]],
    profiles: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    if not activities:
        return "Keine Aktivitäten ausgewählt.", "local"
    fastest = max(metrics, key=lambda item: float(item.get("avg_speed_mps") or 0))
    efficient = [item for item in metrics if item.get("efficiency_kmh_per_bpm") is not None]
    best_efficiency = max(efficient, key=lambda item: float(item["efficiency_kmh_per_bpm"])) if efficient else None
    local = f"{fastest['title']} war mit {float(fastest['avg_speed_mps']) * 3.6:.1f} km/h die schnellste Auswahl."
    if best_efficiency:
        local += f" {best_efficiency['title']} zeigte das beste Verhältnis aus Tempo und durchschnittlicher Herzfrequenz."
    headwinds = [item for item in metrics if isinstance(item.get("headwind_kmh"), (int, float))]
    if headwinds:
        toughest_wind = max(headwinds, key=lambda item: float(item["headwind_kmh"]))
        if float(toughest_wind["headwind_kmh"]) > 1:
            local += f" Besonders einzuordnen ist {toughest_wind['title']} wegen der stärksten Gegenwindkomponente."
    local += " Vergleiche für die Trainingssteuerung vor allem ähnliche Distanzen und Höhenprofile."
    if not settings.openai_api_key:
        return local, "local"
    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=settings.ai_timeout_seconds,
            max_retries=1,
        )
        response = client.responses.create(
            model=settings.openai_model,
            instructions=(
                "Du bist ein deutschsprachiger Radsport-Coach. Vergleiche die ausgewählten Fahrten in 4 bis 6 "
                "prägnanten Sätzen. Berücksichtige Tempo, Herzfrequenzeffizienz, Höhenmeter und Wind. Benenne "
                "klar, welche Einheit in welchem Aspekt überzeugt, ohne medizinische Aussagen oder erfundene Werte."
            ),
            input=f"Gesamtmetriken: {metrics}\nNormalisierte Streckenverläufe: {profiles or []}",
            max_output_tokens=500,
            store=False,
        )
        text = response.output_text.strip()
        return (text, "openai") if text else (local, "local_fallback")
    except Exception:
        return local, "local_fallback"
