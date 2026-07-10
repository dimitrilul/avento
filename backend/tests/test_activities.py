from __future__ import annotations

from fastapi.testclient import TestClient

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

    stats = client.get("/api/v1/statistics/overview", headers=auth)
    assert stats.status_code == 200
    assert stats.json()["activity_count"] == 1
    assert stats.json()["distance_m"] == 600
    assert stats.json()["by_month"][0]["month"] == "2026-06"

    deleted = client.delete(f"/api/v1/activities/{activity_id}", headers=auth)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/activities/{activity_id}", headers=auth).status_code == 404


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

