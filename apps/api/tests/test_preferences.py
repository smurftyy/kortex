"""Tests for GET/PUT /api/v1/preferences."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fakes import FakeClient
from tests.helpers import TEST_USER_ID, make_preferences_row, make_token

VALID_PUT_BODY = {
    "boards_enabled": ["greenhouse", "lever"],
    "location_filter": ["remote", "lagos"],
    "excluded_keywords": ["senior"],
    "digest_time_local": "08:00",
    "digest_timezone": "Africa/Lagos",
    "match_score_threshold": 2.0,
}


def _patch_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client(access_token: str):
        return fake

    monkeypatch.setattr("app.api.routes.preferences.get_user_scoped_client", fake_get_client)


def test_get_preferences_returns_row(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(preferences=[make_preferences_row()])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == TEST_USER_ID


def test_get_preferences_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/preferences")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_preferences_with_no_row_returns_404(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(preferences=[])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PREFERENCES_NOT_FOUND"


def test_put_preferences_creates_row_returns_201(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(preferences=[])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.put(
        "/api/v1/preferences",
        json=VALID_PUT_BODY,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == TEST_USER_ID
    assert body["boards_enabled"] == ["greenhouse", "lever"]
    assert len(fake.table("preferences").rows) == 1


def test_put_preferences_replaces_existing_row_returns_200(
    client: TestClient, monkeypatch
) -> None:
    fake = FakeClient(preferences=[make_preferences_row()])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.put(
        "/api/v1/preferences",
        json=VALID_PUT_BODY,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location_filter"] == ["remote", "lagos"]
    assert len(fake.table("preferences").rows) == 1


def test_put_preferences_without_token_returns_401(client: TestClient) -> None:
    response = client.put("/api/v1/preferences", json=VALID_PUT_BODY)

    assert response.status_code == 401


def test_put_preferences_rejects_missing_required_field(client: TestClient) -> None:
    body = dict(VALID_PUT_BODY)
    del body["match_score_threshold"]

    token = make_token()
    response = client.put(
        "/api/v1/preferences",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_put_preferences_rejects_wrong_type(client: TestClient) -> None:
    body = dict(VALID_PUT_BODY)
    body["match_score_threshold"] = "not-a-number"

    token = make_token()
    response = client.put(
        "/api/v1/preferences",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_put_preferences_rejects_unknown_field(client: TestClient) -> None:
    body = dict(VALID_PUT_BODY)
    body["some_unknown_field"] = "x"

    token = make_token()
    response = client.put(
        "/api/v1/preferences",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_cross_user_cannot_read_or_write_other_users_preferences(
    client: TestClient, monkeypatch
) -> None:
    """Cross-user isolation: GET/PUT always filter by the caller's own JWT id."""

    from tests.helpers import TEST_USER_ID_B

    row_a = make_preferences_row(user_id=TEST_USER_ID)
    fake = FakeClient(preferences=[row_a])
    _patch_client(monkeypatch, fake)

    token_b = make_token(sub=TEST_USER_ID_B)

    # User B has no row of their own yet -> 404, never sees User A's row.
    get_response = client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert get_response.status_code == 404

    # User B's PUT creates their own row; User A's row is untouched.
    put_response = client.put(
        "/api/v1/preferences",
        json=VALID_PUT_BODY,
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert put_response.status_code == 201
    assert put_response.json()["user_id"] == TEST_USER_ID_B

    rows = fake.table("preferences").rows
    assert len(rows) == 2
    row_a_after = next(r for r in rows if r["user_id"] == TEST_USER_ID)
    assert row_a_after["boards_enabled"] == row_a["boards_enabled"]
