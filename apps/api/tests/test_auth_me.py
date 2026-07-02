"""Tests for GET /api/v1/auth/me."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from tests.helpers import TEST_USER_ID, make_token

PROFILE_ROW = {
    "id": TEST_USER_ID,
    "full_name": "Ada Lovelace",
    "phone": None,
    "location": "Lagos, Nigeria",
    "github_url": None,
    "portfolio_url": None,
    "linkedin_url": None,
    "experience_level": "junior",
    "target_roles": ["Backend"],
    "skills": ["Python"],
    "resume_url": None,
    "resume_text": None,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def _fake_client(row: dict | None):
    """Stand in for the RLS-scoped Supabase client's query chain."""

    response = SimpleNamespace(data=row) if row is not None else None
    execute = AsyncMock(return_value=response)
    maybe_single = SimpleNamespace(execute=execute)
    eq = SimpleNamespace(maybe_single=lambda: maybe_single)
    select = SimpleNamespace(eq=lambda *a, **k: eq)
    table = SimpleNamespace(select=lambda *a, **k: select)
    return SimpleNamespace(table=lambda *a, **k: table)


def test_me_returns_profile_for_valid_token(client: TestClient, monkeypatch) -> None:
    async def fake_get_client(access_token: str):
        return _fake_client(PROFILE_ROW)

    monkeypatch.setattr("app.api.routes.auth.get_user_scoped_client", fake_get_client)

    token = make_token()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == TEST_USER_ID
    assert body["full_name"] == "Ada Lovelace"


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_malformed_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_expired_token_returns_401(client: TestClient) -> None:
    token = make_token(expired=True)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_valid_token_but_no_profile_returns_404(
    client: TestClient, monkeypatch
) -> None:
    async def fake_get_client(access_token: str):
        return _fake_client(None)

    monkeypatch.setattr("app.api.routes.auth.get_user_scoped_client", fake_get_client)

    token = make_token()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"
