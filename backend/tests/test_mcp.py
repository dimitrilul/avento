from __future__ import annotations

import json
from datetime import timezone
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import mcp_models  # noqa: F401 - registers MCP tables before the database fixture runs
from app.database import SessionLocal
from app.main import app
from app.mcp_models import MCP_SCOPES, McpAccessToken, McpAuditLog, McpClient
from app.mcp_security import (
    MAX_TOOL_RESULT_BYTES,
    aware_utc,
    hash_access_token,
    mcp_token_ttl_seconds,
    verify_client_secret,
)
from app.mcp_service import McpToolError, serialize_tool_result
from app.models import User
from app.routers.mcp import RPC_PATH, router as mcp_router
from conftest import SAMPLE_TCX


if not any(getattr(route, "path", None) == RPC_PATH for route in app.routes):
    # Production integration is intentionally documented rather than changing app/main.py.
    app.include_router(mcp_router)


RPC_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2025-06-18",
}


def _user_id(email: str) -> str:
    with SessionLocal() as db:
        return db.scalar(select(User.id).where(User.email == email))


def _create_client(
    client: TestClient,
    admin_auth: dict[str, str],
    owner_user_id: str,
    scopes: list[str] | tuple[str, ...] = MCP_SCOPES,
    *,
    name: str = "Test MCP",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/mcp/clients",
        headers=admin_auth,
        json={"owner_user_id": owner_user_id, "name": name, "scopes": list(scopes)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _token(client: TestClient, credentials: dict[str, Any], scopes: list[str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_id": credentials["client_id"],
        "client_secret": credentials["client_secret"],
    }
    if scopes is not None:
        payload["scopes"] = scopes
    response = client.post("/api/v1/mcp/token", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _rpc(
    client: TestClient,
    access_token: str,
    request_id: int | str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    extra_headers: dict[str, str] | None = None,
):
    headers = {**RPC_HEADERS, "Authorization": f"Bearer {access_token}"}
    if extra_headers:
        headers.update(extra_headers)
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return client.post(RPC_PATH, headers=headers, json=message)


def _upload(client: TestClient, auth: dict[str, str], title: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/activities",
        headers=auth,
        files={"file": (f"{title}.tcx", SAMPLE_TCX, "application/xml")},
        data={"title": title, "type": "training"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _register_rider(client: TestClient, admin_auth: dict[str, str]) -> tuple[str, dict[str, str]]:
    invitation = client.post(
        "/api/v1/auth/invitations",
        headers=admin_auth,
        json={"email": "rider@example.com"},
    )
    assert invitation.status_code == 201
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rider@example.com",
            "password": "rider-secure-password",
            "display_name": "Rider",
            "invite_token": invitation.json()["token"],
        },
    )
    assert registration.status_code == 201, registration.text
    rider_id = _user_id("rider@example.com")
    return rider_id, {"Authorization": f"Bearer {registration.json()['access_token']}"}


def _assert_no_internal_mcp_data(value: object) -> None:
    forbidden_keys = {"user_id", "owner_user_id", "client_id", "access_token", "audit"}
    if isinstance(value, dict):
        assert forbidden_keys.isdisjoint(value)
        for child in value.values():
            _assert_no_internal_mcp_data(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_internal_mcp_data(child)


def test_admin_client_credentials_are_hashed_and_tokens_are_hard_limited(
    client: TestClient,
    auth: dict[str, str],
    monkeypatch,
):
    admin_id = _user_id("admin@example.com")
    created = _create_client(client, auth, admin_id)
    assert created["client_secret"].startswith("avmcp_secret_")
    assert created["is_active"] is True
    assert created["scopes"] == list(MCP_SCOPES)
    assert client.get("/api/v1/mcp/clients", headers=auth).json()[0].get("client_secret") is None

    with SessionLocal() as db:
        stored_client = db.scalar(select(McpClient).where(McpClient.client_id == created["client_id"]))
        assert stored_client.secret_hash != created["client_secret"]
        assert verify_client_secret(created["client_secret"], stored_client.secret_hash)

    wrong_secret = f"{created['client_secret']}-wrong"
    rejected = client.post(
        "/api/v1/mcp/token",
        json={"client_id": created["client_id"], "client_secret": wrong_secret},
    )
    assert rejected.status_code == 401
    assert wrong_secret not in rejected.text

    token = _token(client, created)
    assert token["access_token"].startswith("avmcp_at_")
    assert 60 <= token["expires_in"] <= 15 * 60
    assert "client_id" not in token
    with SessionLocal() as db:
        stored_token = db.scalar(
            select(McpAccessToken).where(
                McpAccessToken.token_hash == hash_access_token(token["access_token"])
            )
        )
        assert stored_token is not None
        assert token["access_token"] not in stored_token.token_hash
        remaining = (aware_utc(stored_token.expires_at) - aware_utc(stored_token.created_at)).total_seconds()
        assert 0 < remaining <= 15 * 60

    import app.mcp_security as mcp_security

    monkeypatch.setattr(
        mcp_security,
        "get_settings",
        lambda: SimpleNamespace(mcp_access_token_minutes=99_999),
    )
    assert mcp_token_ttl_seconds() == 15 * 60

    rotated = client.post(
        f"/api/v1/mcp/clients/{created['client_id']}/rotate-secret",
        headers=auth,
    )
    assert rotated.status_code == 200
    assert rotated.json()["client_secret"] != created["client_secret"]
    assert client.post(
        "/api/v1/mcp/token",
        json={"client_id": created["client_id"], "client_secret": created["client_secret"]},
    ).status_code == 401

    revoked = client.post(f"/api/v1/mcp/clients/{created['client_id']}/revoke", headers=auth)
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False
    assert client.post(
        "/api/v1/mcp/token",
        json={
            "client_id": created["client_id"],
            "client_secret": rotated.json()["client_secret"],
        },
    ).status_code == 401


def test_mcp_protocol_metadata_structured_results_and_audit(
    client: TestClient,
    auth: dict[str, str],
):
    activity = _upload(client, auth, "MCP-Ausfahrt")
    credentials = _create_client(client, auth, _user_id("admin@example.com"))
    token = _token(client, credentials)["access_token"]

    initialized = _rpc(
        client,
        token,
        1,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    )
    assert initialized.status_code == 200, initialized.text
    initialize_result = initialized.json()["result"]
    assert initialize_result["protocolVersion"] == "2025-06-18"
    assert initialize_result["capabilities"] == {"tools": {"listChanged": False}}
    assert 20 < len(initialize_result["instructions"]) < 300
    assert credentials["client_id"] not in initialized.text
    assert credentials["client_secret"] not in initialized.text
    assert token not in initialized.text

    notification = client.post(
        RPC_PATH,
        headers={**RPC_HEADERS, "Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert notification.status_code == 202
    assert not notification.content

    stream = client.get(
        RPC_PATH,
        headers={"Accept": "text/event-stream", "Authorization": f"Bearer {token}"},
    )
    assert stream.status_code == 405
    assert stream.headers["allow"] == "POST"

    listed = _rpc(client, token, 2, "tools/list", {})
    assert listed.status_code == 200, listed.text
    tools = listed.json()["result"]["tools"]
    assert {tool["name"] for tool in tools} == {
        "list_activities",
        "get_activity_details",
        "get_statistics",
        "get_records_and_insights",
    }
    for tool in tools:
        assert tool["title"]
        assert tool["inputSchema"]["type"] == "object"
        assert tool["outputSchema"]["type"] == "object"
        assert tool["annotations"] == {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        }

    calls = (
        (3, "list_activities", {}),
        (4, "get_activity_details", {"activity_id": activity["id"]}),
        (
            5,
            "get_statistics",
            {"date_from": "2026-06-01", "date_to": "2026-06-30", "granularity": "day"},
        ),
        (6, "get_records_and_insights", {}),
    )
    for request_id, name, arguments in calls:
        response = _rpc(
            client,
            token,
            request_id,
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        assert response.status_code == 200, response.text
        assert "result" in response.json(), (name, response.text)
        result = response.json()["result"]
        assert result["isError"] is False
        assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
        _assert_no_internal_mcp_data(result["structuredContent"])
        assert credentials["client_id"] not in response.text
        assert token not in response.text

    with SessionLocal() as db:
        audits = db.scalars(select(McpAuditLog).order_by(McpAuditLog.created_at)).all()
        assert len(audits) == 8
        assert all(entry.client_pk is not None for entry in audits)
        assert {entry.outcome for entry in audits} <= {"success", "accepted", "rejected"}
        assert any(entry.method == "http/get" and entry.http_status == 405 for entry in audits)
        stored_audit = json.dumps(
            [
                {
                    "request_id_hash": entry.request_id_hash,
                    "method": entry.method,
                    "tool_name": entry.tool_name,
                    "outcome": entry.outcome,
                    "error_type": entry.error_type,
                }
                for entry in audits
            ]
        )
        assert token not in stored_audit
        assert credentials["client_secret"] not in stored_audit


def test_mcp_tenant_isolation_and_argument_limits(client: TestClient, auth: dict[str, str]):
    admin_activity = _upload(client, auth, "Nur Admin")
    rider_id, rider_auth = _register_rider(client, auth)
    assert client.get("/api/v1/mcp/clients", headers=rider_auth).status_code == 403
    rider_activity = _upload(client, rider_auth, "Nur Rider")
    credentials = _create_client(client, auth, rider_id)
    token = _token(client, credentials)["access_token"]

    listed = _rpc(
        client,
        token,
        1,
        "tools/call",
        {"name": "list_activities", "arguments": {}},
    ).json()["result"]["structuredContent"]
    assert listed["total"] == 1
    assert listed["items"][0]["activity_id"] == rider_activity["id"]
    assert admin_activity["id"] not in json.dumps(listed)

    foreign_details = _rpc(
        client,
        token,
        2,
        "tools/call",
        {"name": "get_activity_details", "arguments": {"activity_id": admin_activity["id"]}},
    ).json()["result"]
    assert foreign_details["isError"] is True
    assert admin_activity["title"] not in json.dumps(foreign_details)

    injected_owner = _rpc(
        client,
        token,
        3,
        "tools/call",
        {
            "name": "list_activities",
            "arguments": {"user_id": _user_id("admin@example.com")},
        },
    ).json()["result"]
    assert injected_owner["isError"] is True
    assert "user_id" not in json.dumps(injected_owner)

    excessive_page = _rpc(
        client,
        token,
        4,
        "tools/call",
        {"name": "list_activities", "arguments": {"limit": 51}},
    ).json()["result"]
    assert excessive_page["isError"] is True

    excessive_period = _rpc(
        client,
        token,
        5,
        "tools/call",
        {
            "name": "get_statistics",
            "arguments": {"date_from": "1900-01-01", "date_to": "2026-01-01"},
        },
    ).json()["result"]
    assert excessive_period["isError"] is True


def test_mcp_scopes_rejections_origin_size_limits_and_identifiable_audit(
    client: TestClient,
    auth: dict[str, str],
):
    credentials = _create_client(
        client,
        auth,
        _user_id("admin@example.com"),
        ["activities:read"],
    )
    token = _token(client, credentials)["access_token"]
    excessive_scope = client.post(
        "/api/v1/mcp/token",
        json={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "scopes": ["statistics:read"],
        },
    )
    assert excessive_scope.status_code == 401
    bad_token_origin = client.post(
        "/api/v1/mcp/token",
        headers={"Origin": "https://evil.example"},
        json={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
        },
    )
    assert bad_token_origin.status_code == 403

    tools = _rpc(client, token, 1, "tools/list", {}).json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["list_activities"]
    denied = _rpc(
        client,
        token,
        2,
        "tools/call",
        {"name": "get_statistics", "arguments": {}},
    )
    assert denied.status_code == 200
    assert denied.json()["error"]["code"] == -32601

    bad_origin = _rpc(
        client,
        token,
        3,
        "tools/list",
        {},
        extra_headers={"Origin": "https://evil.example"},
    )
    assert bad_origin.status_code == 403

    oversized_marker = "sensitive-value-that-must-not-be-audited"
    oversized_message = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/list",
            "params": {"padding": oversized_marker * 4_000},
        }
    )
    oversized = client.post(
        RPC_PATH,
        headers={
            **RPC_HEADERS,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        content=oversized_message,
    )
    assert oversized.status_code == 413

    unknown_marker = "secret-looking-unknown-method"
    unknown = _rpc(client, token, 5, unknown_marker, {})
    assert unknown.status_code == 200
    assert unknown.json()["error"]["code"] == -32601

    disabled = client.patch(
        f"/api/v1/mcp/clients/{credentials['client_id']}",
        headers=auth,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    rejected_token = _rpc(client, token, 6, "tools/list", {})
    assert rejected_token.status_code == 401

    with SessionLocal() as db:
        stored_client = db.scalar(select(McpClient).where(McpClient.client_id == credentials["client_id"]))
        audits = db.scalars(select(McpAuditLog).order_by(McpAuditLog.created_at)).all()
        assert len(audits) == 6
        assert all(entry.client_pk == stored_client.id for entry in audits)
        assert any(entry.error_type == "invalid_origin" for entry in audits)
        assert any(entry.error_type == "payload_too_large" for entry in audits)
        assert any(entry.error_type in {"revoked_token", "inactive_client"} for entry in audits)
        assert any(entry.method == "unknown" and entry.error_type == "unknown_method" for entry in audits)
        audit_values = json.dumps(
            [
                [entry.method, entry.tool_name, entry.outcome, entry.error_type, entry.request_id_hash]
                for entry in audits
            ]
        )
        assert token not in audit_values
        assert oversized_marker not in audit_values
        assert unknown_marker not in audit_values

    try:
        serialize_tool_result({"value": "x" * (MAX_TOOL_RESULT_BYTES + 1)})
    except McpToolError as exc:
        assert exc.error_type == "result_too_large"
    else:
        raise AssertionError("Die Ergebnisgrößenbegrenzung wurde nicht erzwungen.")
