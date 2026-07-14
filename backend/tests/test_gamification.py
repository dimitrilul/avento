from __future__ import annotations

from typing import Any

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from conftest import SAMPLE_TCX
from app.config import get_settings
from app.database import engine
from app.models import Activity


def test_private_gamification_overview_goals_and_challenges(client: TestClient, auth: dict[str, str]):
    uploaded = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": ("gamification.tcx", SAMPLE_TCX, "application/xml")},
    )
    assert uploaded.status_code == 201, uploaded.text

    overview = client.get("/api/v1/gamification/overview", headers=auth)
    assert overview.status_code == 200, overview.text
    data = overview.json()
    assert data["privacy"] == "private"
    assert data["level"]["total_xp"] > 0
    assert data["badges"]
    assert any(badge["key"] == "first_ride" and badge["unlocked"] for badge in data["badges"])
    assert len(data["challenge_suggestions"]) >= 1
    assert len(data["record_chases"]) == 3
    assert len(data["annual_awards"]) == 4

    created = client.post(
        "/api/v1/gamification/goals",
        headers=auth,
        json={
            "title": "Kleine Testmarke",
            "metric": "distance_m",
            "target_value": 500,
            "period": "lifetime",
        },
    )
    assert created.status_code == 201, created.text
    goal = created.json()
    assert goal["status"] == "completed"
    assert goal["current_value"] == 600

    suggested = next(item for item in data["challenge_suggestions"] if item["status"] == "suggested")
    accepted = client.post(
        f"/api/v1/gamification/challenges/{suggested['id']}/accept",
        headers=auth,
        json={},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"


def test_gamification_endpoints_are_owner_scoped(client: TestClient, auth: dict[str, str]):
    created = client.post(
        "/api/v1/gamification/goals",
        headers=auth,
        json={"title": "Privates Ziel", "metric": "activity_count", "target_value": 2, "period": "month"},
    )
    assert created.status_code == 201, created.text
    goal_id = created.json()["id"]

    invitation = client.post("/api/v1/auth/invitations", headers=auth, json={}).json()
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "gamification-second@example.com",
            "password": "second-secure-password",
            "display_name": "Zweites Konto",
            "invite_token": invitation["token"],
        },
    )
    assert registration.status_code == 201, registration.text
    other = {"Authorization": f"Bearer {registration.json()['access_token']}"}

    assert client.patch(f"/api/v1/gamification/goals/{goal_id}", headers=other, json={"title": "Fremd"}).status_code == 404
    assert client.delete(f"/api/v1/gamification/goals/{goal_id}", headers=other).status_code == 404
    assert client.get("/api/v1/gamification/overview", headers=other).json()["goals"] == []


def test_ai_challenges_are_unavailable_without_openai_key(client: TestClient, auth: dict[str, str]):
    response = client.post("/api/v1/gamification/challenges/ai-suggestions", headers=auth)
    assert response.status_code == 404


def test_locationiq_backfill_is_resumable_and_independent_from_weather(
    client: TestClient,
    auth: dict[str, str],
    monkeypatch,
):
    uploaded = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": ("locationiq-backfill.tcx", SAMPLE_TCX, "application/xml")},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["weather_status"] == "unavailable"

    settings = get_settings()
    monkeypatch.setattr(settings, "reverse_geocoding_provider", "locationiq")
    monkeypatch.setattr(settings, "reverse_geocoding_base_url", "https://eu1.locationiq.com/v1")
    monkeypatch.setattr(settings, "locationiq_api_key", "private-integration-key")
    monkeypatch.setattr(settings, "reverse_geocoding_max_samples", 1)

    def requester(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "address": {
                    "city": "Berlin",
                    "state": "Berlin",
                    "country": "Deutschland",
                    "country_code": "de",
                }
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", requester)

    result = client.post(
        "/api/v1/gamification/discoveries/backfill",
        headers=auth,
        json={"limit": 5, "retry_failed": False},
    )
    assert result.status_code == 200, result.text
    assert result.json() == {
        "processed": 1,
        "available": 1,
        "failed": 0,
        "remaining": 0,
        "total": 1,
        "rate_limited": False,
        "retry_after_seconds": None,
    }

    overview = client.get("/api/v1/gamification/overview", headers=auth).json()
    assert overview["geocoding"]["status"] == "ready"
    assert overview["geocoding"]["attribution_label"] == "Search by LocationIQ.com"
    assert next(item for item in overview["discoveries"] if item["scope"] == "municipality")["places"] == ["Berlin"]

    with Session(engine) as db:
        activity = db.scalar(select(Activity))
        assert activity is not None
        assert activity.weather_status == "unavailable"
        assert activity.geography_status == "available"
        assert "private-integration-key" not in repr(activity.geography_data)
