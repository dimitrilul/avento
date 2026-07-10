from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient


def _pkce(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _oauth_setup(client: TestClient) -> tuple[str, str, str]:
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "oauth-password", "display_name": "Admin"},
    )
    assert bootstrap.status_code == 201, bootstrap.text
    registered = client.post(
        "/oauth/register",
        json={"client_name": "Test MCP", "redirect_uris": ["http://127.0.0.1:8765/callback"]},
    )
    assert registered.status_code == 201, registered.text
    return registered.json()["client_id"], "http://127.0.0.1:8765/callback", "oauth-password"


def test_mcp_oauth_discovery_authorization_code_refresh_and_rpc(client: TestClient):
    client_id, redirect_uri, password = _oauth_setup(client)
    resource = "http://testserver/api/v1/mcp/rpc"
    metadata = client.get("/.well-known/oauth-protected-resource")
    assert metadata.status_code == 200
    assert metadata.json()["resource"] == resource
    assert client.get("/.well-known/oauth-authorization-server").json()["token_endpoint"] == "http://testserver/oauth/token"

    verifier = "a" * 64
    authorization = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "activities:read statistics:read",
            "state": "state-123",
            "code_challenge": _pkce(verifier),
            "code_challenge_method": "S256",
            "resource": resource,
        },
    )
    assert authorization.status_code == 200
    assert "Test MCP" in authorization.text

    approved = client.post(
        "/oauth/authorize",
        data={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "activities:read statistics:read",
            "state": "state-123",
            "code_challenge": _pkce(verifier),
            "code_challenge_method": "S256",
            "resource": resource,
            "email": "admin@example.com",
            "password": password,
            "decision": "allow",
        },
        follow_redirects=False,
    )
    assert approved.status_code == 302
    callback = urlsplit(approved.headers["location"])
    callback_query = parse_qs(callback.query)
    assert callback_query["state"] == ["state-123"]
    code = callback_query["code"][0]

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
            "resource": resource,
        },
    )
    assert token.status_code == 200, token.text
    tokens = token.json()
    assert tokens["token_type"] == "Bearer"
    assert tokens["scope"] == "activities:read statistics:read"

    rpc = client.post(
        "/api/v1/mcp/rpc",
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-06-18",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert rpc.status_code == 200, rpc.text
    assert [tool["name"] for tool in rpc.json()["result"]["tools"]] == ["list_activities", "get_statistics"]

    refreshed = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
            "resource": resource,
        },
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]
    assert client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": tokens["refresh_token"],
            "resource": resource,
        },
    ).status_code == 400


def test_mcp_oauth_rejects_open_redirects_and_wrong_resource(client: TestClient):
    client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "oauth-password", "display_name": "Admin"},
    )
    open_redirect = client.post(
        "/oauth/register",
        json={"client_name": "Unsafe", "redirect_uris": ["https://example.com/callback"]},
    )
    assert open_redirect.status_code == 201
    client_id = open_redirect.json()["client_id"]
    response = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "https://example.com/callback",
            "code_challenge": _pkce("b" * 64),
            "code_challenge_method": "S256",
            "resource": "https://other.example/mcp",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert parse_qs(urlsplit(response.headers["location"]).query)["error"] == ["invalid_target"]
