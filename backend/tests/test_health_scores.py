from __future__ import annotations

import json
import math
from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.health_scores import (
    ALGORITHM_VERSION,
    DailyHealthData,
    build_personal_baselines,
    calculate_energy_score,
    calculate_health_scores,
    calculate_recovery_score,
    calculate_resilience_score,
    calculate_training_load,
    training_load_from_zones,
)


TARGET = date(2026, 7, 12)


def _day(day: date, **changes) -> DailyHealthData:
    values = {
        "date": day,
        "sleep_minutes": 480.0,
        "sleep_efficiency_percent": 90.0,
        "hrv_rmssd_ms": 50.0,
        "resting_heart_rate_bpm": 60.0,
        "training_load": 40.0,
        "active_minutes": 60.0,
        "steps": 8_000,
        "is_complete": True,
    }
    values.update(changes)
    return DailyHealthData(**values)


def _history(days: int = 30) -> list[DailyHealthData]:
    return [_day(TARGET - timedelta(days=offset)) for offset in range(days, 0, -1)]


def test_personal_baselines_are_robust_and_exclude_target_day():
    history = _history(30)
    history[0] = replace(history[0], hrv_rmssd_ms=1_000.0)
    history.append(_day(TARGET, hrv_rmssd_ms=900.0))

    baselines = build_personal_baselines(history, TARGET, "hrv_rmssd_ms")

    assert [item.window_days for item in baselines] == [7, 14, 30]
    assert [item.valid_days for item in baselines] == [7, 14, 30]
    assert all(item.eligible for item in baselines)
    assert baselines[-1].median == 50.0
    assert baselines[-1].mad == 0.0
    assert baselines[-1].robust_scale == 3.0


@pytest.mark.parametrize(
    ("days", "expected_eligible"),
    [(4, []), (5, [7]), (10, [7, 14]), (21, [7, 14, 30])],
)
def test_baseline_minimum_data_rules(days: int, expected_eligible: list[int]):
    baselines = build_personal_baselines(_history(days), TARGET, "sleep_minutes")
    assert [item.window_days for item in baselines if item.eligible] == expected_eligible


def test_recovery_at_personal_baseline_is_70_and_explainable():
    result = calculate_recovery_score(_day(TARGET), _history())
    payload = result.to_dict()

    assert result.value == 70
    assert result.status == "available"
    assert result.level == "typisch"
    assert result.confidence == "hoch"
    assert result.coverage == 1.0
    assert {factor["key"] for factor in payload["factors"]} == {
        "hrv",
        "resting_heart_rate",
        "sleep_duration",
        "sleep_efficiency",
    }
    assert payload["algorithm_version"] == ALGORITHM_VERSION
    assert payload["calculation"] == "deterministic_plain_python_no_ai"
    assert "keine medizinische Diagnose" in payload["disclaimer"]


def test_recovery_without_hrv_is_available_but_less_certain():
    current = _day(TARGET, hrv_rmssd_ms=None)
    result = calculate_recovery_score(current, _history())

    assert result.value == 70
    assert result.status == "available"
    assert result.coverage == 0.75
    assert result.confidence == "mittel"
    hrv = next(factor for factor in result.factors if factor.key == "hrv")
    assert hrv.status == "missing_current_data"


def test_recovery_without_resting_heart_rate_is_available_but_less_certain():
    current = _day(TARGET, resting_heart_rate_bpm=None)
    result = calculate_recovery_score(current, _history())

    assert result.value == 70
    assert result.status == "available"
    assert result.coverage == 0.75
    resting = next(factor for factor in result.factors if factor.key == "resting_heart_rate")
    assert resting.status == "missing_current_data"


def test_recovery_is_null_when_both_autonomic_core_signals_are_missing():
    current = _day(TARGET, hrv_rmssd_ms=None, resting_heart_rate_bpm=None)
    result = calculate_recovery_score(current, _history())

    assert result.value is None
    assert result.status == "missing_required_data"
    assert "HRV oder Ruhepuls" in result.missing_required_signals
    assert result.confidence == "keine"


def test_recovery_is_null_without_sleep_or_on_incomplete_day():
    missing_sleep = calculate_recovery_score(_day(TARGET, sleep_minutes=None), _history())
    incomplete = calculate_recovery_score(_day(TARGET, is_complete=False), _history())

    assert missing_sleep.value is None
    assert missing_sleep.status == "missing_required_data"
    assert incomplete.value is None
    assert incomplete.status == "incomplete_data"


def test_recovery_is_null_with_insufficient_baseline():
    result = calculate_recovery_score(_day(TARGET), _history(4))

    assert result.value is None
    assert result.status == "insufficient_baseline"


@pytest.mark.parametrize(
    ("days", "expected_confidence"),
    [(5, "niedrig"), (10, "mittel"), (21, "hoch")],
)
def test_recovery_confidence_uses_longest_qualified_window(days: int, expected_confidence: str):
    result = calculate_recovery_score(_day(TARGET), _history(days))
    assert result.status == "available"
    assert result.confidence == expected_confidence


def test_recovery_factors_are_clamped_to_score_boundaries():
    high = calculate_recovery_score(
        _day(
            TARGET,
            sleep_minutes=1_440,
            sleep_efficiency_percent=100,
            hrv_rmssd_ms=1_000,
            resting_heart_rate_bpm=20,
        ),
        _history(),
    )
    low = calculate_recovery_score(
        _day(
            TARGET,
            sleep_minutes=1,
            sleep_efficiency_percent=0,
            hrv_rmssd_ms=0.1,
            resting_heart_rate_bpm=250,
        ),
        _history(),
    )

    assert 0 <= high.value <= 100
    assert 0 <= low.value <= 100
    assert all(0 <= factor.factor_score <= 100 for factor in high.factors if factor.available)
    assert all(0 <= factor.factor_score <= 100 for factor in low.factors if factor.available)


def test_recovery_lists_largest_deterministic_influence_first():
    result = calculate_recovery_score(_day(TARGET, hrv_rmssd_ms=80), _history()).to_dict()

    assert result["important_factors"][0]["key"] == "hrv"
    assert result["important_factors"][0]["impact"] == "positiv"
    assert result["important_factors"][0]["contribution_points"] > 0


def test_energy_at_baseline_is_70_and_uses_completed_previous_day():
    result = calculate_energy_score(_day(TARGET), _history())

    assert result.value == 70
    assert result.status == "available"
    assert result.confidence == "hoch"
    assert result.coverage == 1.0
    assert result.metadata["day_demand_source"] == "previous_complete_local_day"


def test_energy_is_null_without_recovery_core_data():
    current = _day(TARGET, hrv_rmssd_ms=None, resting_heart_rate_bpm=None)
    result = calculate_energy_score(current, _history())

    assert result.value is None
    assert result.status == "missing_required_data"
    assert result.metadata["recovery_status"] == "missing_required_data"


def test_energy_does_not_convert_missing_previous_day_data_to_zero():
    history = [row for row in _history() if row.date != TARGET - timedelta(days=1)]
    result = calculate_energy_score(_day(TARGET), history)

    assert result.status == "available"
    assert result.coverage == 0.7
    missing = {factor.key: factor.status for factor in result.factors}
    assert missing["previous_day_load"] == "missing_current_data"
    assert missing["previous_day_activity"] == "missing_current_data"


def test_google_health_zone_load_formula_is_exact_and_case_insensitive():
    load = training_load_from_zones(
        {"LIGHT": 30, "moderate": 20, "Vigorous": 10, "peak": 5}
    )
    assert load == 120.0
    assert training_load_from_zones({}) == 0.0


def test_training_load_returns_raw_value_and_relative_index():
    result = calculate_training_load(_day(TARGET), _history())

    assert result.raw_value == 40.0
    assert result.raw_unit == "Belastungspunkte"
    assert result.value == 50
    assert result.level == "typisch"
    assert result.status == "available"
    assert result.metadata["windows"]["7"]["total_load"] == 280.0


def test_training_load_can_be_derived_from_google_health_zones():
    current = _day(
        TARGET,
        training_load=None,
        heart_rate_zone_minutes={"light": 30, "moderate": 20, "vigorous": 10, "peak": 5},
    )
    result = calculate_training_load(current, _history())

    assert result.raw_value == 120.0
    assert result.metadata["load_method"] == "google_health_heart_rate_zones"
    assert result.value > 50
    assert result.level == "sehr_hoch"


def test_training_load_keeps_raw_value_when_baseline_is_insufficient():
    result = calculate_training_load(_day(TARGET), _history(4))

    assert result.value is None
    assert result.raw_value == 40.0
    assert result.status == "insufficient_baseline"


def test_training_load_is_null_when_source_data_is_missing():
    result = calculate_training_load(
        _day(TARGET, training_load=None, heart_rate_zone_minutes=None),
        _history(),
    )
    assert result.value is None
    assert result.raw_value is None
    assert result.status == "missing_required_data"


def test_resilience_requires_at_least_21_scorable_days():
    insufficient = calculate_resilience_score(_day(TARGET), _history(20))
    sufficient = calculate_resilience_score(_day(TARGET), _history(21))

    assert insufficient.value is None
    assert insufficient.status == "insufficient_baseline"
    assert sufficient.value is not None
    assert sufficient.status == "available"
    assert sufficient.metadata["valid_recovery_days"] == 21


def test_resilience_uses_rebound_only_after_three_high_load_events():
    history = _history()
    for offset in (4, 10, 16, 22):
        index = next(i for i, row in enumerate(history) if row.date == TARGET - timedelta(days=offset))
        history[index] = replace(history[index], training_load=100.0)

    result = calculate_resilience_score(_day(TARGET), history)
    rebound = next(factor for factor in result.factors if factor.key == "load_rebound")

    assert result.status == "available"
    assert result.confidence == "hoch"
    assert result.metadata["high_load_events_with_follow_up"] == 4
    assert rebound.status == "available"
    assert rebound.factor_score == 70.0


def test_all_results_are_deterministic_and_json_serializable():
    current = _day(TARGET, hrv_rmssd_ms=61.25, resting_heart_rate_bpm=57)
    history = _history()

    first = calculate_health_scores(current, history)
    second = calculate_health_scores(current, list(reversed(history)))

    assert first == second
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
        second,
        sort_keys=True,
        ensure_ascii=False,
    )
    assert first["algorithm_version"] == ALGORITHM_VERSION
    assert first["source"] == "google_health_api"
    assert "no_ai" in first["calculation"]


def test_invalid_or_ambiguous_input_is_rejected():
    with pytest.raises(ValueError, match="endlich"):
        _day(TARGET, hrv_rmssd_ms=math.nan)
    with pytest.raises(ValueError, match="Unbekannte"):
        training_load_from_zones({"zone-5": 10})
    with pytest.raises(ValueError, match="Mehrere normalisierte Tageswerte"):
        calculate_recovery_score(_day(TARGET), [_day(TARGET - timedelta(days=1))] * 2)


def test_dictionary_input_uses_supported_aliases():
    current = {
        "date": TARGET.isoformat(),
        "sleep_minutes": 480,
        "sleep_efficiency_percent": 90,
        "hrv_ms": 50,
        "resting_hr_bpm": 60,
        "training_load": 40,
        "active_minutes": 60,
        "steps": 8_000,
    }
    history = [
        {
            "date": row.date.isoformat(),
            "sleep_minutes": row.sleep_minutes,
            "sleep_efficiency_percent": row.sleep_efficiency_percent,
            "hrv_ms": row.hrv_rmssd_ms,
            "resting_hr_bpm": row.resting_heart_rate_bpm,
            "training_load": row.training_load,
            "active_minutes": row.active_minutes,
            "steps": row.steps,
        }
        for row in _history()
    ]

    assert calculate_health_scores(current, history)["recovery"]["value"] == 70
