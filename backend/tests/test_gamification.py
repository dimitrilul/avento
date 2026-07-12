from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import SAMPLE_TCX


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
