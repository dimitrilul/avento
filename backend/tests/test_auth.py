from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import PasswordResetToken, utcnow
from app.security import token_hash


def test_bootstrap_login_refresh_rotation_and_profile(client: TestClient):
    payload = {"email": "rider@example.com", "password": "a-really-secure-password", "display_name": "Rider"}
    first = client.post("/api/v1/auth/bootstrap", json=payload)
    assert first.status_code == 201
    assert client.post("/api/v1/auth/bootstrap", json=payload).status_code == 409

    login = client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != refresh_token
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401

    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    profile = client.get("/api/v1/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["is_admin"] is True
    assert len(profile.json()["hr_zones"]) == 5
    assert profile.json()["ui_mode"] == "classic"
    updated = client.patch("/api/v1/profile", headers=headers, json={"hr_max": 200, "hr_rest": 55})
    assert updated.status_code == 200
    assert updated.json()["hr_max"] == 200

    minimal = client.patch("/api/v1/profile", headers=headers, json={"ui_mode": "minimal"})
    assert minimal.status_code == 200
    assert minimal.json()["ui_mode"] == "minimal"
    assert client.get("/api/v1/profile", headers=headers).json()["ui_mode"] == "minimal"
    invalid = client.patch("/api/v1/profile", headers=headers, json={"ui_mode": "neon"})
    assert invalid.status_code == 422


def test_bootstrap_code_and_invitation_registration(client: TestClient):
    get_settings().bootstrap_invite_code = "one-time-secret"
    payload = {"email": "admin@example.com", "password": "a-really-secure-password", "display_name": "Admin"}
    assert client.post("/api/v1/auth/bootstrap", json=payload).status_code == 403
    payload["bootstrap_code"] = "one-time-secret"
    bootstrap = client.post("/api/v1/auth/bootstrap", json=payload)
    assert bootstrap.status_code == 201
    headers = {"Authorization": f"Bearer {bootstrap.json()['access_token']}"}

    invitation = client.post(
        "/api/v1/auth/invitations", headers=headers, json={"email": "friend@example.com", "expires_in_days": 2}
    )
    assert invitation.status_code == 201
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "friend@example.com",
            "password": "another-secure-password",
            "display_name": "Friend",
            "invite_token": invitation.json()["token"],
        },
    )
    assert registration.status_code == 201


def test_admin_password_reset_is_one_time_and_revokes_sessions(client: TestClient):
    admin = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "admin-secure-password", "display_name": "Admin"},
    ).json()
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    invitation = client.post(
        "/api/v1/auth/invitations", headers=admin_headers, json={"email": "rider@example.com"}
    ).json()
    rider = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rider@example.com",
            "password": "old-secure-password",
            "display_name": "Rider",
            "invite_token": invitation["token"],
        },
    ).json()
    rider_headers = {"Authorization": f"Bearer {rider['access_token']}"}

    forbidden = client.post(
        "/api/v1/auth/password-resets", headers=rider_headers, json={"email": "rider@example.com"}
    )
    assert forbidden.status_code == 403

    first = client.post(
        "/api/v1/auth/password-resets", headers=admin_headers, json={"email": "rider@example.com"}
    )
    second = client.post(
        "/api/v1/auth/password-resets",
        headers=admin_headers,
        json={"email": "rider@example.com", "expires_in_minutes": 30},
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["email"] == "rider@example.com"
    assert client.post(
        "/api/v1/auth/password-reset",
        json={"token": first.json()["token"], "new_password": "ignored-new-password"},
    ).status_code == 400

    used = client.post(
        "/api/v1/auth/password-reset",
        json={"token": second.json()["token"], "new_password": "new-secure-password"},
    )
    assert used.status_code == 204
    assert client.post(
        "/api/v1/auth/password-reset",
        json={"token": second.json()["token"], "new_password": "another-new-password"},
    ).status_code == 400
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rider["refresh_token"]}).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": "rider@example.com", "password": "old-secure-password"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": "rider@example.com", "password": "new-secure-password"}
    ).status_code == 200


def test_password_reset_rejects_expired_and_invalid_tokens(client: TestClient):
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "admin-secure-password", "display_name": "Admin"},
    ).json()
    headers = {"Authorization": f"Bearer {bootstrap['access_token']}"}
    reset = client.post(
        "/api/v1/auth/password-resets", headers=headers, json={"email": "admin@example.com"}
    ).json()
    with SessionLocal() as db:
        stored = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash(reset["token"])))
        stored.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    expired = client.post(
        "/api/v1/auth/password-reset",
        json={"token": reset["token"], "new_password": "new-secure-password"},
    )
    invalid = client.post(
        "/api/v1/auth/password-reset",
        json={"token": "this-is-a-long-enough-invalid-reset-token", "new_password": "new-secure-password"},
    )
    assert expired.status_code == invalid.status_code == 400
    assert expired.json()["detail"] == invalid.json()["detail"]


def test_authenticated_password_change_requires_current_password(client: TestClient):
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "old-secure-password", "display_name": "Admin"},
    ).json()
    headers = {"Authorization": f"Bearer {bootstrap['access_token']}"}
    wrong = client.post(
        "/api/v1/profile/password",
        headers=headers,
        json={"current_password": "wrong-password", "new_password": "new-secure-password"},
    )
    assert wrong.status_code == 400
    changed = client.post(
        "/api/v1/profile/password",
        headers=headers,
        json={"current_password": "old-secure-password", "new_password": "new-secure-password"},
    )
    assert changed.status_code == 204
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": bootstrap["refresh_token"]}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "old-secure-password"}
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "new-secure-password"}
    ).status_code == 200
