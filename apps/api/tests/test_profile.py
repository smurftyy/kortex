"""Tests for PATCH /api/v1/profile."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fakes import FakeClient
from tests.helpers import TEST_USER_ID, make_profile_row, make_token


def _patch_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client(access_token: str):
        return fake

    monkeypatch.setattr("app.api.routes.profile.get_user_scoped_client", fake_get_client)


def test_patch_profile_updates_and_returns_row(client: TestClient, monkeypatch) -> None:
    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"location": "Nairobi, Kenya"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Nairobi, Kenya"
    assert body["full_name"] == "Ada Lovelace"
    assert row["location"] == "Nairobi, Kenya"


def test_patch_profile_without_token_returns_401(client: TestClient) -> None:
    response = client.patch("/api/v1/profile", json={"location": "Nairobi, Kenya"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_patch_profile_with_no_row_returns_404(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"location": "Nairobi, Kenya"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_patch_profile_rejects_unknown_field(client: TestClient) -> None:
    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"not_a_real_field": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_patch_profile_rejects_wrong_type(client: TestClient) -> None:
    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"skills": "should-be-a-list-not-a-string"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_patch_profile_rejects_null_for_not_null_column(client: TestClient) -> None:
    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"full_name": None},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_patch_profile_allows_null_for_nullable_column(client: TestClient, monkeypatch) -> None:
    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.patch(
        "/api/v1/profile",
        json={"phone": None},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_patch_profile_cannot_reach_another_users_row(client: TestClient, monkeypatch) -> None:
    """Cross-user isolation: PATCH always filters by the caller's own JWT id."""

    from tests.helpers import TEST_USER_ID_B

    row_a = make_profile_row(user_id=TEST_USER_ID, full_name="User A")
    row_b = make_profile_row(user_id=TEST_USER_ID_B, full_name="User B")
    fake = FakeClient(profiles=[row_a, row_b])
    _patch_client(monkeypatch, fake)

    token_b = make_token(sub=TEST_USER_ID_B)
    response = client.patch(
        "/api/v1/profile",
        json={"full_name": "User B Updated"},
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == TEST_USER_ID_B
    assert response.json()["full_name"] == "User B Updated"
    # User A's row must be untouched by User B's write.
    assert row_a["full_name"] == "User A"
