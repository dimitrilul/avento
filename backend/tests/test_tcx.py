from __future__ import annotations

import pytest

from app.tcx import TcxError, _elevation_gain, default_hr_zones, parse_tcx
from conftest import SAMPLE_TCX


def test_parse_tcx_metrics_and_sensors():
    parsed = parse_tcx(SAMPLE_TCX, default_hr_zones(190))

    assert parsed.activity_type == "cycling"
    assert parsed.distance_m == 600
    assert parsed.duration_s == 180
    assert parsed.moving_time_s == 120
    assert parsed.pause_time_s == 60
    assert parsed.avg_speed_mps == 5
    assert parsed.max_speed_mps == 5
    assert parsed.elevation_gain_m == 10
    assert parsed.avg_hr_bpm == 132.5
    assert parsed.max_hr_bpm == 160
    assert parsed.avg_cadence_rpm == 77.5
    assert parsed.max_power_w == 220
    assert len(parsed.track_points) == 4
    assert parsed.training_load > 0


def test_rejects_non_tcx_and_xml_entities():
    with pytest.raises(TcxError):
        parse_tcx(b"<root />", default_hr_zones(190))

    malicious = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><TrainingCenterDatabase>&e;</TrainingCenterDatabase>'
    with pytest.raises(TcxError):
        parse_tcx(malicious, default_hr_zones(190))


def test_elevation_gain_keeps_long_gentle_climbs_and_filters_small_noise():
    gentle_climb = [50 + index * 0.25 for index in range(481)]
    assert _elevation_gain(gentle_climb) == pytest.approx(120, abs=0.5)

    flat_with_sensor_noise = [50, 50.4, 49.7, 50.3, 49.8, 50.2, 49.9, 50.1]
    assert _elevation_gain(flat_with_sensor_noise) == 0
