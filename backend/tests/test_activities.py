from __future__ import annotations

import io
import zipfile
from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine
from app.models import Activity
from conftest import SAMPLE_TCX


def test_activity_crud_analysis_weather_summary_and_statistics(client: TestClient, auth: dict[str, str]):
    uploaded = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": ("ride.tcx", SAMPLE_TCX, "application/vnd.garmin.tcx+xml")},
        data={"title": "Morgenrunde", "type": "training", "notes": "Locker"},
    )
    assert uploaded.status_code == 201, uploaded.text
    activity = uploaded.json()
    activity_id = activity["id"]
    assert activity["distance_m"] == 600
    assert activity["moving_time_s"] == 120
    assert activity["weather_status"] == "unavailable"

    duplicate = client.post(
        "/api/v1/activities", headers=auth, files={"file": ("copy.tcx", SAMPLE_TCX, "application/xml")}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["activity_id"] == activity_id

    listing = client.get("/api/v1/activities?q=Morgen&type=training", headers=auth)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    track = client.get(f"/api/v1/activities/{activity_id}/track", headers=auth)
    assert len(track.json()["points"]) == 4

    patched = client.patch(
        f"/api/v1/activities/{activity_id}", headers=auth, json={"title": "Abendrunde", "notes": None}
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Abendrunde"
    assert patched.json()["notes"] is None

    weather = client.post(f"/api/v1/activities/{activity_id}/weather/refresh", headers=auth)
    assert weather.status_code == 200
    assert weather.json()["status"] == "unavailable"
    summary = client.post(f"/api/v1/activities/{activity_id}/summary", headers=auth)
    assert summary.status_code == 200
    assert summary.json()["provider"] == "local"
    assert "0.6 km" in summary.json()["summary"]

    reanalyzed = client.post(f"/api/v1/activities/{activity_id}/reanalyze", headers=auth)
    assert reanalyzed.status_code == 200
    assert reanalyzed.json()["elevation_gain_m"] == 10
    assert reanalyzed.json()["ai_summary"] is None

    stats = client.get("/api/v1/statistics/overview", headers=auth)
    assert stats.status_code == 200
    assert stats.json()["activity_count"] == 1
    assert stats.json()["distance_m"] == 600
    assert stats.json()["by_month"][0]["month"] == "2026-06"

    filtered_stats = client.get("/api/v1/statistics/overview?type=training", headers=auth)
    assert filtered_stats.status_code == 200
    assert filtered_stats.json()["activity_count"] == 1
    assert filtered_stats.json()["distance_m"] == 600
    assert client.get("/api/v1/statistics/overview?type=commute", headers=auth).json()["activity_count"] == 0

    deleted = client.delete(f"/api/v1/activities/{activity_id}", headers=auth)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/activities/{activity_id}", headers=auth).status_code == 404


def test_quality_exclusion_export_and_saved_segment(client: TestClient, auth: dict[str, str]):
    uploaded = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": ("export-ride.tcx", SAMPLE_TCX, "application/xml")},
    )
    assert uploaded.status_code == 201, uploaded.text
    activity = uploaded.json()
    activity_id = activity["id"]
    assert activity["metric_provenance"]["distance"]["source"] == "TCX/FIT/GPX"
    assert any(flag["code"] == "missing_power" for flag in activity["data_quality_flags"]) is False

    excluded = client.patch(f"/api/v1/activities/{activity_id}", headers=auth, json={"include_in_statistics": False})
    assert excluded.status_code == 200
    assert client.get("/api/v1/statistics/overview", headers=auth).json()["activity_count"] == 0

    archive = client.post("/api/v1/activities/export", headers=auth, json={"activity_ids": [activity_id], "redact_private_data": True})
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as files:
        names = files.namelist()
        assert "manifest.json" in names
        assert any(name.endswith(".csv") for name in names)
        assert not any(name.startswith("original/") for name in names)

    segment = client.post("/api/v1/segments", headers=auth, json={"activity_id": activity_id, "name": "Kernstück", "start_m": 0, "end_m": 300})
    assert segment.status_code == 201, segment.text
    assert segment.json()["metrics"]["distance_m"] == 300
    assert client.get("/api/v1/segments", headers=auth).json()[0]["name"] == "Kernstück"


def test_users_cannot_access_each_others_activities(client: TestClient, auth: dict[str, str]):
    uploaded = client.post(
        "/api/v1/activities", headers=auth, files={"file": ("ride.tcx", SAMPLE_TCX, "application/xml")}
    )
    activity_id = uploaded.json()["id"]
    invitation = client.post("/api/v1/auth/invitations", headers=auth, json={}).json()
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "second@example.com",
            "password": "second-secure-password",
            "display_name": "Second",
            "invite_token": invitation["token"],
        },
    )
    second = {"Authorization": f"Bearer {registration.json()['access_token']}"}
    assert client.get(f"/api/v1/activities/{activity_id}", headers=second).status_code == 404
    assert client.get("/api/v1/activities", headers=second).json()["total"] == 0


def test_new_activity_geocodes_with_locationiq_when_weather_is_unavailable(
    client: TestClient,
    auth: dict[str, str],
    monkeypatch,
):
    settings = get_settings()
    monkeypatch.setattr(settings, "reverse_geocoding_provider", "locationiq")
    monkeypatch.setattr(settings, "reverse_geocoding_base_url", "https://eu1.locationiq.com/v1")
    monkeypatch.setattr(settings, "locationiq_api_key", "private-upload-key")
    monkeypatch.setattr(settings, "reverse_geocoding_max_samples", 1)

    def requester(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={"address": {"city": "Berlin", "state": "Berlin", "country": "Deutschland", "country_code": "de"}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", requester)
    uploaded = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": ("locationiq-new.tcx", SAMPLE_TCX, "application/xml")},
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["weather_status"] == "unavailable"

    with Session(engine) as db:
        activity = db.scalar(select(Activity))
        assert activity is not None
        assert activity.geography_status == "available"
        assert activity.geography_data["route_places"]

    overview = client.get("/api/v1/gamification/overview", headers=auth).json()
    assert next(item for item in overview["discoveries"] if item["scope"] == "municipality")["count"] == 1
