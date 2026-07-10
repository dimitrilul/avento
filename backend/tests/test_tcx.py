from __future__ import annotations

import pytest

from app.tcx import TcxError, default_hr_zones, parse_tcx
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

