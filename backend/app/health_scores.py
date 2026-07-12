"""Deterministische Wellness-Scores für Daten aus der Google Health API.

Das Modul ist absichtlich frei von Datenbank-, Netzwerk- und KI-Abhängigkeiten.
Es verarbeitet bereits normalisierte Tageswerte und gibt ausschließlich
reproduzierbare Dataclasses beziehungsweise serialisierbare Dictionaries aus.

Die Scores sind persönliche Fitness- und Wellness-Einschätzungen. Sie dürfen
nicht als Diagnose, Krankheitsrisiko oder medizinische Handlungsempfehlung
verwendet werden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Any, Iterable, Mapping, Sequence


ALGORITHM_VERSION = "google-health-wellness-v1.0.0"
SOURCE_NAME = "google_health_api"
WELLNESS_DISCLAIMER = (
    "Diese Werte sind deterministische Fitness- und Wellness-Einschätzungen auf Basis persönlicher "
    "Vergleichswerte. Sie sind keine medizinische Diagnose, bewerten kein Krankheitsrisiko und "
    "ersetzen keine ärztliche Beratung."
)

BASELINE_WINDOWS: tuple[int, ...] = (7, 14, 30)
MINIMUM_BASELINE_DAYS: dict[int, int] = {7: 5, 14: 10, 30: 21}
ZONE_LOAD_WEIGHTS: dict[str, float] = {
    "light": 1.0,
    "moderate": 2.0,
    "vigorous": 3.0,
    "peak": 4.0,
}


@dataclass(frozen=True, slots=True)
class DailyHealthData:
    """Normalisierte Tagesdaten aus der Google Health API.

    ``date`` ist der von Google gelieferte lokale Kalendertag. Schlaf wird dem
    Tag zugerechnet, an dem der Hauptschlaf endet. Prozentwerte liegen zwischen
    0 und 100. ``None`` bedeutet fehlend; eine echte Null bleibt eine Null.
    """

    date: date
    sleep_minutes: float | None = None
    sleep_efficiency_percent: float | None = None
    hrv_rmssd_ms: float | None = None
    resting_heart_rate_bpm: float | None = None
    training_load: float | None = None
    heart_rate_zone_minutes: Mapping[str, float] | None = None
    active_minutes: float | None = None
    steps: int | None = None
    is_complete: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.date, datetime) or not isinstance(self.date, date):
            raise TypeError("date muss ein datetime.date ohne Uhrzeit sein.")
        _validate_optional_number("sleep_minutes", self.sleep_minutes, minimum=0, maximum=1_440)
        _validate_optional_number(
            "sleep_efficiency_percent",
            self.sleep_efficiency_percent,
            minimum=0,
            maximum=100,
        )
        _validate_optional_number("hrv_rmssd_ms", self.hrv_rmssd_ms, minimum=0, maximum=1_000)
        _validate_optional_number(
            "resting_heart_rate_bpm",
            self.resting_heart_rate_bpm,
            minimum=20,
            maximum=250,
        )
        _validate_optional_number("training_load", self.training_load, minimum=0, maximum=1_000_000)
        _validate_optional_number("active_minutes", self.active_minutes, minimum=0, maximum=1_440)
        if self.steps is not None:
            if isinstance(self.steps, bool) or not isinstance(self.steps, int):
                raise TypeError("steps muss eine ganze Zahl sein.")
            if not 0 <= self.steps <= 10_000_000:
                raise ValueError("steps liegt außerhalb des unterstützten Bereichs.")
        if not isinstance(self.is_complete, bool):
            raise TypeError("is_complete muss boolesch sein.")
        if self.heart_rate_zone_minutes is not None:
            training_load_from_zones(self.heart_rate_zone_minutes)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DailyHealthData":
        """Erzeugt Tagesdaten aus einem API-nahen Dictionary.

        Für die beiden häufigsten normalisierten Kurzformen werden Aliase
        akzeptiert. Alle weiteren Felder bleiben bewusst explizit.
        """

        raw_date = value.get("date")
        parsed_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
        return cls(
            date=parsed_date,
            sleep_minutes=value.get("sleep_minutes"),
            sleep_efficiency_percent=value.get("sleep_efficiency_percent"),
            hrv_rmssd_ms=value.get("hrv_rmssd_ms", value.get("hrv_ms")),
            resting_heart_rate_bpm=value.get(
                "resting_heart_rate_bpm",
                value.get("resting_hr_bpm"),
            ),
            training_load=value.get("training_load"),
            heart_rate_zone_minutes=value.get("heart_rate_zone_minutes"),
            active_minutes=value.get("active_minutes"),
            steps=value.get("steps"),
            is_complete=value.get("is_complete", True),
        )

    @property
    def resolved_training_load(self) -> float | None:
        if self.training_load is not None:
            return float(self.training_load)
        if self.heart_rate_zone_minutes is None:
            return None
        return training_load_from_zones(self.heart_rate_zone_minutes)

    @property
    def training_load_method(self) -> str | None:
        if self.training_load is not None:
            return "provided_daily_load"
        if self.heart_rate_zone_minutes is not None:
            return "google_health_heart_rate_zones"
        return None


@dataclass(frozen=True, slots=True)
class BaselineStats:
    window_days: int
    required_days: int
    valid_days: int
    coverage: float
    median: float | None
    mad: float | None
    robust_scale: float | None
    eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_days": self.window_days,
            "required_days": self.required_days,
            "valid_days": self.valid_days,
            "coverage": self.coverage,
            "median": self.median,
            "mad": self.mad,
            "robust_scale": self.robust_scale,
            "eligible": self.eligible,
        }


@dataclass(frozen=True, slots=True)
class ScoreFactor:
    key: str
    label: str
    weight: float
    unit: str | None
    source_data_types: tuple[str, ...]
    current_value: float | None = None
    baseline_value: float | None = None
    baseline_window_days: int | None = None
    robust_z: float | None = None
    factor_score: float | None = None
    contribution_points: float = 0.0
    impact: str = "unavailable"
    status: str = "missing_current_data"
    reason: str | None = None
    baselines: tuple[BaselineStats, ...] = ()

    @property
    def available(self) -> bool:
        return self.factor_score is not None and self.status == "available"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "unit": self.unit,
            "source_data_types": list(self.source_data_types),
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "baseline_window_days": self.baseline_window_days,
            "robust_z": self.robust_z,
            "factor_score": self.factor_score,
            "contribution_points": self.contribution_points,
            "impact": self.impact,
            "status": self.status,
            "reason": self.reason,
            "baselines": [baseline.to_dict() for baseline in self.baselines],
        }


@dataclass(frozen=True, slots=True)
class ScoreResult:
    key: str
    label: str
    target_date: date
    value: int | None
    unit: str
    status: str
    level: str | None
    confidence: str
    coverage: float
    factors: tuple[ScoreFactor, ...] = ()
    missing_required_signals: tuple[str, ...] = ()
    raw_value: float | None = None
    raw_unit: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    algorithm_version: str = ALGORITHM_VERSION
    disclaimer: str = WELLNESS_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        available_factors = [factor for factor in self.factors if factor.available]
        important = sorted(
            available_factors,
            key=lambda factor: (-abs(factor.contribution_points), factor.key),
        )[:3]
        return {
            "key": self.key,
            "label": self.label,
            "target_date": self.target_date.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "raw_value": self.raw_value,
            "raw_unit": self.raw_unit,
            "status": self.status,
            "level": self.level,
            "confidence": self.confidence,
            "data_coverage": {
                "fraction": self.coverage,
                "percent": _round_half_up(self.coverage * 100, 1),
                "missing_required_signals": list(self.missing_required_signals),
            },
            "important_factors": [factor.to_dict() for factor in important],
            "factors": [factor.to_dict() for factor in self.factors],
            "metadata": _plain_mapping(self.metadata),
            "algorithm_version": self.algorithm_version,
            "calculation": "deterministic_plain_python_no_ai",
            "source": SOURCE_NAME,
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True, slots=True)
class _MetricSpec:
    label: str
    unit: str
    absolute_scale_floor: float
    relative_scale_floor: float = 0.0


_METRIC_SPECS: dict[str, _MetricSpec] = {
    "sleep_minutes": _MetricSpec("Schlafdauer", "min", 30.0, 0.08),
    "sleep_efficiency_percent": _MetricSpec("Schlafeffizienz", "%", 3.0, 0.0),
    "hrv_rmssd_ms": _MetricSpec("Herzfrequenzvariabilität", "ms RMSSD", 3.0, 0.05),
    "resting_heart_rate_bpm": _MetricSpec("Ruhepuls", "bpm", 2.0, 0.03),
    "training_load": _MetricSpec("Trainingsbelastung", "Belastungspunkte", 5.0, 0.10),
    "active_minutes": _MetricSpec("Aktive Minuten", "min", 10.0, 0.10),
    "steps": _MetricSpec("Schritte", "Schritte", 500.0, 0.10),
}


def _validate_optional_number(
    name: str,
    value: float | None,
    *,
    minimum: float,
    maximum: float,
) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} muss eine Zahl sein.")
    if not math.isfinite(float(value)):
        raise ValueError(f"{name} muss endlich sein.")
    if not minimum <= float(value) <= maximum:
        raise ValueError(f"{name} liegt außerhalb des unterstützten Bereichs.")


def _round_half_up(value: float, digits: int = 0) -> int | float:
    quantum = Decimal("1").scaleb(-digits)
    rounded = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    return int(rounded) if digits == 0 else float(rounded)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _plain_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, BaselineStats):
            result[key] = item.to_dict()
        elif isinstance(item, Mapping):
            result[key] = _plain_mapping(item)
        elif isinstance(item, tuple):
            result[key] = [entry.to_dict() if isinstance(entry, BaselineStats) else entry for entry in item]
        else:
            result[key] = item
    return result


def training_load_from_zones(zone_minutes: Mapping[str, float]) -> float:
    """Berechnet Belastungspunkte aus Google-Health-Herzfrequenzzonen.

    Formel: LIGHT×1 + MODERATE×2 + VIGOROUS×3 + PEAK×4. Ein leeres
    Mapping ist eine echte Null; ``None`` wird auf Tagesebene als fehlend
    behandelt. Unbekannte Zonen werden nicht stillschweigend verworfen.
    """

    total = 0.0
    seen: set[str] = set()
    for raw_zone, raw_minutes in zone_minutes.items():
        zone = str(raw_zone).strip().lower()
        if zone not in ZONE_LOAD_WEIGHTS:
            raise ValueError(f"Unbekannte Google-Health-Herzfrequenzzone: {raw_zone}")
        if zone in seen:
            raise ValueError(f"Herzfrequenzzone doppelt vorhanden: {raw_zone}")
        seen.add(zone)
        _validate_optional_number(
            f"heart_rate_zone_minutes[{raw_zone}]",
            raw_minutes,
            minimum=0,
            maximum=1_440,
        )
        total += float(raw_minutes) * ZONE_LOAD_WEIGHTS[zone]
    return float(_round_half_up(total, 2))


def _coerce_day(value: DailyHealthData | Mapping[str, Any]) -> DailyHealthData:
    return value if isinstance(value, DailyHealthData) else DailyHealthData.from_dict(value)


def _normalize_history(
    history: Iterable[DailyHealthData | Mapping[str, Any]],
) -> tuple[DailyHealthData, ...]:
    rows = sorted((_coerce_day(row) for row in history), key=lambda row: row.date)
    dates: set[date] = set()
    for row in rows:
        if row.date in dates:
            raise ValueError(f"Mehrere normalisierte Tageswerte für {row.date.isoformat()}.")
        dates.add(row.date)
    return tuple(rows)


def _metric_value(day: DailyHealthData, metric: str) -> float | None:
    if metric == "training_load":
        return day.resolved_training_load
    value = getattr(day, metric)
    return float(value) if value is not None else None


def _is_valid_for_score(metric: str, value: float | None) -> bool:
    if value is None or not math.isfinite(value):
        return False
    if metric in {"sleep_minutes", "hrv_rmssd_ms"}:
        return value > 0
    return value >= 0


def build_personal_baselines(
    history: Iterable[DailyHealthData | Mapping[str, Any]],
    target_date: date,
    metric: str,
) -> tuple[BaselineStats, ...]:
    """Erstellt robuste, leckagefreie 7-/14-/30-Tage-Baselines.

    Der Zieltag und zukünftige Werte fließen nie ein. Als Lage wird der Median,
    als Streuung ``1.4826 × MAD`` mit metrikspezifischem Mindestwert verwendet.
    """

    if metric not in _METRIC_SPECS:
        raise ValueError(f"Unbekannte Baseline-Metrik: {metric}")
    rows = _normalize_history(history)
    spec = _METRIC_SPECS[metric]
    baselines: list[BaselineStats] = []
    for window_days in BASELINE_WINDOWS:
        window_start = target_date - timedelta(days=window_days)
        values = [
            value
            for row in rows
            if window_start <= row.date < target_date
            and row.is_complete
            and _is_valid_for_score(metric, value := _metric_value(row, metric))
        ]
        count = len(values)
        required = MINIMUM_BASELINE_DAYS[window_days]
        center = float(median(values)) if values else None
        mad = float(median(abs(value - center) for value in values)) if center is not None else None
        scale_floor = (
            max(spec.absolute_scale_floor, abs(center) * spec.relative_scale_floor)
            if center is not None
            else None
        )
        scale = max(1.4826 * mad, scale_floor) if mad is not None and scale_floor is not None else None
        baselines.append(
            BaselineStats(
                window_days=window_days,
                required_days=required,
                valid_days=count,
                coverage=float(_round_half_up(count / window_days, 3)),
                median=float(_round_half_up(center, 4)) if center is not None else None,
                mad=float(_round_half_up(mad, 4)) if mad is not None else None,
                robust_scale=float(_round_half_up(scale, 4)) if scale is not None else None,
                eligible=count >= required,
            )
        )
    return tuple(baselines)


def _primary_baseline(baselines: Sequence[BaselineStats]) -> BaselineStats | None:
    return next((baseline for baseline in reversed(baselines) if baseline.eligible), None)


def _robust_z(value: float, baseline: BaselineStats) -> float:
    assert baseline.median is not None and baseline.robust_scale is not None
    return _clamp((value - baseline.median) / baseline.robust_scale, -3.0, 3.0)


def _metric_factor(
    *,
    key: str,
    day: DailyHealthData,
    history: Sequence[DailyHealthData],
    metric: str,
    weight: float,
    direction: float,
    source_data_types: tuple[str, ...],
    upper_z_cap: float | None = None,
    base_score: float = 70.0,
    points_per_z: float = 12.5,
    baseline_target_date: date | None = None,
) -> ScoreFactor:
    spec = _METRIC_SPECS[metric]
    value = _metric_value(day, metric)
    baselines = build_personal_baselines(history, baseline_target_date or day.date, metric)
    if not _is_valid_for_score(metric, value):
        return ScoreFactor(
            key=key,
            label=spec.label,
            weight=weight,
            unit=spec.unit,
            source_data_types=source_data_types,
            current_value=value,
            reason="Für den Zieltag fehlt ein gültiger Wert.",
            baselines=baselines,
        )
    baseline = _primary_baseline(baselines)
    if baseline is None:
        return ScoreFactor(
            key=key,
            label=spec.label,
            weight=weight,
            unit=spec.unit,
            source_data_types=source_data_types,
            current_value=value,
            status="insufficient_baseline",
            reason="Keine 7-, 14- oder 30-Tage-Baseline erfüllt die Mindestabdeckung.",
            baselines=baselines,
        )
    z = _robust_z(value, baseline) * direction
    if upper_z_cap is not None:
        z = min(z, upper_z_cap)
    factor_score = _clamp(base_score + points_per_z * z, 0.0, 100.0)
    return ScoreFactor(
        key=key,
        label=spec.label,
        weight=weight,
        unit=spec.unit,
        source_data_types=source_data_types,
        current_value=float(_round_half_up(value, 4)),
        baseline_value=baseline.median,
        baseline_window_days=baseline.window_days,
        robust_z=float(_round_half_up(z, 4)),
        factor_score=float(_round_half_up(factor_score, 2)),
        impact="neutral",
        status="available",
        baselines=baselines,
    )


def _derived_factor(
    *,
    key: str,
    label: str,
    weight: float,
    score: float | None,
    source_data_types: tuple[str, ...],
    current_value: float | None = None,
    unit: str | None = "Punkte",
    status: str = "available",
    reason: str | None = None,
) -> ScoreFactor:
    return ScoreFactor(
        key=key,
        label=label,
        weight=weight,
        unit=unit,
        source_data_types=source_data_types,
        current_value=current_value,
        factor_score=float(_round_half_up(score, 2)) if score is not None else None,
        impact="neutral" if score is not None else "unavailable",
        status=status if score is not None else status,
        reason=reason,
    )


def _score_level(value: int) -> str:
    if value < 40:
        return "niedrig"
    if value < 60:
        return "eingeschränkt"
    if value < 80:
        return "typisch"
    return "hoch"


def _baseline_confidence(factors: Sequence[ScoreFactor], coverage: float) -> str:
    windows = [factor.baseline_window_days for factor in factors if factor.available and factor.baseline_window_days]
    if windows and min(windows) >= 30 and coverage >= 0.90:
        return "hoch"
    if windows and min(windows) >= 14 and coverage >= 0.70:
        return "mittel"
    return "niedrig"


def _with_contributions(
    factors: Sequence[ScoreFactor],
    available_weight: float,
    neutral_score: float,
) -> tuple[ScoreFactor, ...]:
    result: list[ScoreFactor] = []
    for factor in factors:
        if not factor.available or factor.factor_score is None or available_weight <= 0:
            result.append(factor)
            continue
        contribution = factor.weight / available_weight * (factor.factor_score - neutral_score)
        impact = "positiv" if contribution > 0.5 else "negativ" if contribution < -0.5 else "neutral"
        result.append(
            replace(
                factor,
                contribution_points=float(_round_half_up(contribution, 2)),
                impact=impact,
            )
        )
    return tuple(result)


def _available_result(
    *,
    key: str,
    label: str,
    target_date: date,
    factors: Sequence[ScoreFactor],
    confidence: str | None = None,
    neutral_score: float = 70.0,
    raw_value: float | None = None,
    raw_unit: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ScoreResult:
    available_weight = sum(factor.weight for factor in factors if factor.available)
    score = sum(
        factor.weight * float(factor.factor_score)
        for factor in factors
        if factor.available and factor.factor_score is not None
    ) / available_weight
    value = int(_round_half_up(_clamp(score, 0.0, 100.0)))
    completed_factors = _with_contributions(factors, available_weight, neutral_score)
    coverage = float(_round_half_up(available_weight, 3))
    return ScoreResult(
        key=key,
        label=label,
        target_date=target_date,
        value=value,
        unit="Punkte",
        status="available",
        level=_score_level(value),
        confidence=confidence or _baseline_confidence(completed_factors, coverage),
        coverage=coverage,
        factors=completed_factors,
        raw_value=raw_value,
        raw_unit=raw_unit,
        metadata=metadata or {},
    )


def _unavailable_result(
    *,
    key: str,
    label: str,
    target_date: date,
    status: str,
    factors: Sequence[ScoreFactor] = (),
    missing: Sequence[str] = (),
    raw_value: float | None = None,
    raw_unit: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ScoreResult:
    coverage = sum(factor.weight for factor in factors if factor.available)
    return ScoreResult(
        key=key,
        label=label,
        target_date=target_date,
        value=None,
        unit="Punkte",
        status=status,
        level=None,
        confidence="keine",
        coverage=float(_round_half_up(coverage, 3)),
        factors=tuple(factors),
        missing_required_signals=tuple(missing),
        raw_value=raw_value,
        raw_unit=raw_unit,
        metadata=metadata or {},
    )


def calculate_recovery_score(
    current: DailyHealthData | Mapping[str, Any],
    history: Iterable[DailyHealthData | Mapping[str, Any]],
) -> ScoreResult:
    """Berechnet Recovery aus Schlaf, HRV und Ruhepuls.

    Pflicht sind ein vollständiger Hauptschlaf und mindestens eines der beiden
    autonomen Signale HRV/Ruhepuls. Fehlen beide, wird niemals ein Score
    geschätzt. Ein einzelnes fehlendes autonomes Signal senkt die Abdeckung.
    """

    day = _coerce_day(current)
    rows = _normalize_history(history)
    if not day.is_complete:
        return _unavailable_result(
            key="recovery",
            label="Recovery",
            target_date=day.date,
            status="incomplete_data",
            missing=("vollständiger Zieltag",),
        )
    missing: list[str] = []
    if not _is_valid_for_score("sleep_minutes", _metric_value(day, "sleep_minutes")):
        missing.append("Hauptschlaf")
    if day.hrv_rmssd_ms is None and day.resting_heart_rate_bpm is None:
        missing.append("HRV oder Ruhepuls")
    if missing:
        return _unavailable_result(
            key="recovery",
            label="Recovery",
            target_date=day.date,
            status="missing_required_data",
            missing=missing,
        )

    factors = (
        _metric_factor(
            key="hrv",
            day=day,
            history=rows,
            metric="hrv_rmssd_ms",
            weight=0.25,
            direction=1.0,
            source_data_types=("daily-heart-rate-variability",),
        ),
        _metric_factor(
            key="resting_heart_rate",
            day=day,
            history=rows,
            metric="resting_heart_rate_bpm",
            weight=0.25,
            direction=-1.0,
            source_data_types=("daily-resting-heart-rate",),
        ),
        _metric_factor(
            key="sleep_duration",
            day=day,
            history=rows,
            metric="sleep_minutes",
            weight=0.30,
            direction=1.0,
            upper_z_cap=1.0,
            source_data_types=("sleep",),
        ),
        _metric_factor(
            key="sleep_efficiency",
            day=day,
            history=rows,
            metric="sleep_efficiency_percent",
            weight=0.20,
            direction=1.0,
            upper_z_cap=1.0,
            source_data_types=("sleep",),
        ),
    )
    sleep_factor = next(factor for factor in factors if factor.key == "sleep_duration")
    autonomic = [factor for factor in factors if factor.key in {"hrv", "resting_heart_rate"}]
    if not sleep_factor.available or not any(factor.available for factor in autonomic):
        return _unavailable_result(
            key="recovery",
            label="Recovery",
            target_date=day.date,
            status="insufficient_baseline",
            factors=factors,
            missing=("qualifizierte Schlaf- und autonome Baseline",),
        )
    coverage = sum(factor.weight for factor in factors if factor.available)
    if coverage < 0.55:
        return _unavailable_result(
            key="recovery",
            label="Recovery",
            target_date=day.date,
            status="insufficient_coverage",
            factors=factors,
            missing=("mindestens 55 % gewichtete Datenabdeckung",),
        )
    return _available_result(
        key="recovery",
        label="Recovery",
        target_date=day.date,
        factors=factors,
        metadata={"required_signals": ["sleep", "hrv_or_resting_heart_rate"]},
    )


def _previous_day(rows: Sequence[DailyHealthData], target_date: date) -> DailyHealthData | None:
    wanted = target_date - timedelta(days=1)
    return next((row for row in rows if row.date == wanted and row.is_complete), None)


def calculate_energy_score(
    current: DailyHealthData | Mapping[str, Any],
    history: Iterable[DailyHealthData | Mapping[str, Any]],
    recovery: ScoreResult | None = None,
) -> ScoreResult:
    """Berechnet die Tagesenergie aus Recovery, Schlafreserve und Vortagslast.

    Recovery und eine qualifizierte Schlafdauer sind zentral. Belastung und
    Alltagsaktivität des vollständig abgeschlossenen Vortags sind optionale
    Einflussfaktoren; fehlende Werte werden nie als Null interpretiert.
    """

    day = _coerce_day(current)
    rows = _normalize_history(history)
    recovery_result = recovery or calculate_recovery_score(day, rows)
    if recovery_result.value is None:
        return _unavailable_result(
            key="energy",
            label="Energie",
            target_date=day.date,
            status="missing_required_data",
            missing=("verfügbarer Recovery-Score",),
            metadata={"recovery_status": recovery_result.status},
        )

    recovery_factor = _derived_factor(
        key="recovery",
        label="Recovery",
        weight=0.50,
        score=float(recovery_result.value),
        current_value=float(recovery_result.value),
        source_data_types=("derived:recovery",),
    )
    sleep_factor = _metric_factor(
        key="sleep_reserve",
        day=day,
        history=rows,
        metric="sleep_minutes",
        weight=0.20,
        direction=1.0,
        upper_z_cap=1.0,
        source_data_types=("sleep",),
    )
    previous = _previous_day(rows, day.date)
    if previous is None:
        load_factor = _derived_factor(
            key="previous_day_load",
            label="Belastung am Vortag",
            weight=0.20,
            score=None,
            source_data_types=("exercise", "time-in-heart-rate-zone"),
            status="missing_current_data",
            reason="Der vollständig abgeschlossene Vortag fehlt.",
        )
        activity_factor = _derived_factor(
            key="previous_day_activity",
            label="Alltagsaktivität am Vortag",
            weight=0.10,
            score=None,
            source_data_types=("active-minutes", "steps"),
            status="missing_current_data",
            reason="Der vollständig abgeschlossene Vortag fehlt.",
        )
    else:
        load_factor = _metric_factor(
            key="previous_day_load",
            day=previous,
            history=rows,
            metric="training_load",
            weight=0.20,
            direction=-1.0,
            upper_z_cap=1.0,
            source_data_types=("exercise", "time-in-heart-rate-zone"),
            baseline_target_date=previous.date,
        )
        if previous.active_minutes is not None:
            activity_factor = _metric_factor(
                key="previous_day_activity",
                day=previous,
                history=rows,
                metric="active_minutes",
                weight=0.10,
                direction=-1.0,
                upper_z_cap=1.0,
                source_data_types=("active-minutes",),
                baseline_target_date=previous.date,
            )
        else:
            activity_factor = _metric_factor(
                key="previous_day_activity",
                day=previous,
                history=rows,
                metric="steps",
                weight=0.10,
                direction=-1.0,
                upper_z_cap=1.0,
                source_data_types=("steps",),
                baseline_target_date=previous.date,
            )
    factors = (recovery_factor, sleep_factor, load_factor, activity_factor)
    if not sleep_factor.available:
        return _unavailable_result(
            key="energy",
            label="Energie",
            target_date=day.date,
            status="insufficient_baseline",
            factors=factors,
            missing=("qualifizierte Schlafbaseline",),
        )
    coverage = sum(factor.weight for factor in factors if factor.available)
    if coverage < 0.70:
        return _unavailable_result(
            key="energy",
            label="Energie",
            target_date=day.date,
            status="insufficient_coverage",
            factors=factors,
            missing=("mindestens 70 % gewichtete Datenabdeckung",),
        )
    if recovery_result.confidence == "hoch" and coverage >= 0.90:
        confidence = "hoch"
    elif recovery_result.confidence in {"hoch", "mittel"} and coverage >= 0.80:
        confidence = "mittel"
    else:
        confidence = "niedrig"
    return _available_result(
        key="energy",
        label="Energie",
        target_date=day.date,
        factors=factors,
        confidence=confidence,
        metadata={"day_demand_source": "previous_complete_local_day"},
    )


def _training_level(z: float) -> str:
    if z < -1.0:
        return "unter_persönlichem_niveau"
    if z <= 1.0:
        return "typisch"
    if z <= 2.0:
        return "hoch"
    return "sehr_hoch"


def _window_load_summaries(rows: Sequence[DailyHealthData], target_date: date) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for window in BASELINE_WINDOWS:
        start = target_date - timedelta(days=window)
        values = [
            value
            for row in rows
            if start <= row.date < target_date
            and row.is_complete
            and _is_valid_for_score("training_load", value := row.resolved_training_load)
        ]
        summaries[str(window)] = {
            "valid_days": len(values),
            "total_load": float(_round_half_up(sum(values), 2)) if values else None,
            "weekly_equivalent": (
                float(_round_half_up(sum(values) * 7 / window, 2)) if values else None
            ),
        }
    return summaries


def calculate_training_load(
    current: DailyHealthData | Mapping[str, Any],
    history: Iterable[DailyHealthData | Mapping[str, Any]],
) -> ScoreResult:
    """Berechnet Tageslast und ihre Position zur persönlichen Baseline.

    ``raw_value`` sind die eigentlichen Belastungspunkte. ``value`` ist nur ein
    0–100-Lageindex (50 = persönlicher Median), keine Gütebewertung.
    """

    day = _coerce_day(current)
    rows = _normalize_history(history)
    raw_load = day.resolved_training_load
    metadata: dict[str, Any] = {
        "load_method": day.training_load_method,
        "zone_weights": dict(ZONE_LOAD_WEIGHTS),
        "windows": _window_load_summaries(rows, day.date),
        "index_interpretation": "50 entspricht dem persönlichen Median; höher bedeutet mehr Belastung.",
    }
    if raw_load is None:
        return _unavailable_result(
            key="training_load",
            label="Trainingsbelastung",
            target_date=day.date,
            status="missing_required_data",
            missing=("Trainingsbelastung oder Herzfrequenzzonen",),
            metadata=metadata,
        )
    if not day.is_complete:
        return _unavailable_result(
            key="training_load",
            label="Trainingsbelastung",
            target_date=day.date,
            status="incomplete_data",
            missing=("vollständiger Zieltag",),
            raw_value=raw_load,
            raw_unit="Belastungspunkte",
            metadata=metadata,
        )
    factor = _metric_factor(
        key="daily_training_load",
        day=day,
        history=rows,
        metric="training_load",
        weight=1.0,
        direction=1.0,
        source_data_types=("exercise", "time-in-heart-rate-zone"),
        base_score=50.0,
        points_per_z=15.0,
    )
    if not factor.available:
        return _unavailable_result(
            key="training_load",
            label="Trainingsbelastung",
            target_date=day.date,
            status="insufficient_baseline",
            factors=(factor,),
            missing=("qualifizierte Belastungsbaseline",),
            raw_value=raw_load,
            raw_unit="Belastungspunkte",
            metadata=metadata,
        )
    result = _available_result(
        key="training_load",
        label="Trainingsbelastung",
        target_date=day.date,
        factors=(factor,),
        neutral_score=50.0,
        raw_value=float(_round_half_up(raw_load, 2)),
        raw_unit="Belastungspunkte",
        metadata=metadata,
    )
    assert factor.robust_z is not None
    return replace(result, level=_training_level(factor.robust_z))


def _recovery_proxy(
    day: DailyHealthData,
    baselines: Mapping[str, BaselineStats | None],
) -> float | None:
    if not _is_valid_for_score("sleep_minutes", _metric_value(day, "sleep_minutes")):
        return None
    components: list[tuple[float, float]] = []
    for metric, weight, direction, cap in (
        ("sleep_minutes", 0.40, 1.0, 1.0),
        ("hrv_rmssd_ms", 0.30, 1.0, None),
        ("resting_heart_rate_bpm", 0.30, -1.0, None),
    ):
        value = _metric_value(day, metric)
        baseline = baselines.get(metric)
        if not _is_valid_for_score(metric, value) or baseline is None:
            continue
        z = _robust_z(float(value), baseline) * direction
        if cap is not None:
            z = min(z, cap)
        components.append((weight, _clamp(70.0 + 12.5 * z, 0.0, 100.0)))
    has_sleep = any(weight == 0.40 for weight, _ in components)
    has_autonomic = any(weight == 0.30 for weight, _ in components)
    if not has_sleep or not has_autonomic:
        return None
    total_weight = sum(weight for weight, _ in components)
    return sum(weight * score for weight, score in components) / total_weight


def calculate_resilience_score(
    current: DailyHealthData | Mapping[str, Any],
    history: Iterable[DailyHealthData | Mapping[str, Any]],
) -> ScoreResult:
    """Berechnet langfristige Erholungsfähigkeit aus 30 abgeschlossenen Tagen.

    Mindestens 21 Tage müssen Hauptschlaf und HRV oder Ruhepuls enthalten.
    Belastungs-Rebound wird erst ab drei persönlich hohen Belastungstagen als
    Faktor verwendet; andernfalls bleibt der Score möglich, aber unsicherer.
    """

    day = _coerce_day(current)
    rows = _normalize_history(history)
    window_start = day.date - timedelta(days=30)
    window_rows = tuple(row for row in rows if window_start <= row.date < day.date and row.is_complete)
    baseline_sets = {
        metric: build_personal_baselines(rows, day.date, metric)
        for metric in ("sleep_minutes", "hrv_rmssd_ms", "resting_heart_rate_bpm", "training_load")
    }
    primary = {metric: _primary_baseline(values) for metric, values in baseline_sets.items()}
    proxies_by_date = {
        row.date: proxy
        for row in window_rows
        if (proxy := _recovery_proxy(row, primary)) is not None
    }
    if len(proxies_by_date) < 21:
        return _unavailable_result(
            key="resilience",
            label="Langfristige Resilienz",
            target_date=day.date,
            status="insufficient_baseline",
            missing=("mindestens 21 von 30 Tagen mit Schlaf und HRV oder Ruhepuls",),
            metadata={
                "valid_recovery_days": len(proxies_by_date),
                "required_recovery_days": 21,
                "baselines": baseline_sets,
            },
        )

    proxy_values = list(proxies_by_date.values())
    recovery_level = float(median(proxy_values))
    recovery_mad = float(median(abs(value - recovery_level) for value in proxy_values))
    stability = _clamp(100.0 - 2.5 * recovery_mad, 0.0, 100.0)

    sleep_baseline = primary["sleep_minutes"]
    assert sleep_baseline is not None and sleep_baseline.mad is not None
    sleep_consistency = _clamp(100.0 - sleep_baseline.mad / 3.0, 0.0, 100.0)

    load_baseline = primary["training_load"]
    rebound_values: list[float] = []
    if load_baseline is not None:
        for row in window_rows:
            load = row.resolved_training_load
            if not _is_valid_for_score("training_load", load):
                continue
            if _robust_z(float(load), load_baseline) < 1.0:
                continue
            following = proxies_by_date.get(row.date + timedelta(days=1))
            if following is not None:
                rebound_values.append(_clamp(70.0 + following - recovery_level, 0.0, 100.0))
    rebound_score = float(median(rebound_values)) if len(rebound_values) >= 3 else None

    factors = (
        _derived_factor(
            key="recovery_level",
            label="Typisches Recovery-Niveau",
            weight=0.45,
            score=recovery_level,
            current_value=recovery_level,
            source_data_types=("sleep", "daily-heart-rate-variability", "daily-resting-heart-rate"),
        ),
        _derived_factor(
            key="recovery_stability",
            label="Recovery-Stabilität",
            weight=0.20,
            score=stability,
            current_value=recovery_mad,
            unit="MAD-Punkte",
            source_data_types=("derived:daily-recovery-proxy",),
        ),
        _derived_factor(
            key="load_rebound",
            label="Erholung nach hoher Belastung",
            weight=0.25,
            score=rebound_score,
            current_value=rebound_score,
            source_data_types=("exercise", "time-in-heart-rate-zone", "derived:daily-recovery-proxy"),
            status="available" if rebound_score is not None else "insufficient_events",
            reason=(
                None
                if rebound_score is not None
                else "Weniger als drei hohe Belastungstage mit Folgetagsdaten im 30-Tage-Fenster."
            ),
        ),
        _derived_factor(
            key="sleep_consistency",
            label="Schlafkonsistenz",
            weight=0.10,
            score=sleep_consistency,
            current_value=sleep_baseline.mad,
            unit="min MAD",
            source_data_types=("sleep",),
        ),
    )
    coverage = sum(factor.weight for factor in factors if factor.available)
    if coverage < 0.70:
        return _unavailable_result(
            key="resilience",
            label="Langfristige Resilienz",
            target_date=day.date,
            status="insufficient_coverage",
            factors=factors,
            missing=("mindestens 70 % gewichtete Langzeitdaten",),
        )
    if len(proxies_by_date) >= 25 and len(rebound_values) >= 3:
        confidence = "hoch"
    elif len(rebound_values) >= 3:
        confidence = "mittel"
    else:
        confidence = "niedrig"
    return _available_result(
        key="resilience",
        label="Langfristige Resilienz",
        target_date=day.date,
        factors=factors,
        confidence=confidence,
        metadata={
            "valid_recovery_days": len(proxies_by_date),
            "high_load_events_with_follow_up": len(rebound_values),
            "baselines": baseline_sets,
            "recovery_proxy_method": "robust_median_mad_no_ai",
        },
    )


def calculate_health_scores(
    current: DailyHealthData | Mapping[str, Any],
    history: Iterable[DailyHealthData | Mapping[str, Any]],
) -> dict[str, Any]:
    """Öffentliche Komfort-API für alle vier Analytics-Ergebnisse."""

    day = _coerce_day(current)
    rows = _normalize_history(history)
    recovery = calculate_recovery_score(day, rows)
    energy = calculate_energy_score(day, rows, recovery=recovery)
    training_load = calculate_training_load(day, rows)
    resilience = calculate_resilience_score(day, rows)
    return {
        "target_date": day.date.isoformat(),
        "source": SOURCE_NAME,
        "algorithm_version": ALGORITHM_VERSION,
        "calculation": "deterministic_plain_python_no_ai",
        "recovery": recovery.to_dict(),
        "energy": energy.to_dict(),
        "training_load": training_load.to_dict(),
        "resilience": resilience.to_dict(),
        "disclaimer": WELLNESS_DISCLAIMER,
    }


__all__ = [
    "ALGORITHM_VERSION",
    "BASELINE_WINDOWS",
    "MINIMUM_BASELINE_DAYS",
    "WELLNESS_DISCLAIMER",
    "BaselineStats",
    "DailyHealthData",
    "ScoreFactor",
    "ScoreResult",
    "build_personal_baselines",
    "calculate_energy_score",
    "calculate_health_scores",
    "calculate_recovery_score",
    "calculate_resilience_score",
    "calculate_training_load",
    "training_load_from_zones",
]
