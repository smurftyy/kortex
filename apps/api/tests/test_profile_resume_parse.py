"""Tests for POST /api/v1/profile/resume/parse."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fakes import FakeClient, install_fake_storage_downloads
from tests.helpers import (
    TEST_USER_ID,
    TEST_USER_ID_B,
    make_blank_pdf,
    make_password_protected_pdf,
    make_pdf_with_text,
    make_profile_row,
    make_token,
)


def _patch_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client(access_token: str):
        return fake

    monkeypatch.setattr("app.api.routes.profile.get_user_scoped_client", fake_get_client)


def _seed_uploaded_resume(fake: FakeClient, *, user_id: str, content: bytes) -> dict:
    path = f"{user_id}/resume.pdf"
    row = make_profile_row(user_id=user_id)
    row["resume_url"] = path
    fake.table("profiles").rows.append(row)
    fake.storage.objects[("resumes", path)] = content
    return row


def _parse(client: TestClient, *, sub: str = TEST_USER_ID):
    token = make_token(sub=sub)
    return client.post("/api/v1/profile/resume/parse", headers={"Authorization": f"Bearer {token}"})


def test_parse_success(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    row = _seed_uploaded_resume(
        fake, user_id=TEST_USER_ID, content=make_pdf_with_text("Ada's resume")
    )
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"
    assert "Ada's resume" in body["resume_text"]
    assert row["resume_text"] == body["resume_text"]


def test_parse_corrupt_pdf(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    row = _seed_uploaded_resume(fake, user_id=TEST_USER_ID, content=b"not a real pdf at all")
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "corrupt"
    assert body["resume_text"] is None
    assert row["resume_text"] is None


def test_parse_image_only_pdf_no_text_layer(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    row = _seed_uploaded_resume(fake, user_id=TEST_USER_ID, content=make_blank_pdf())
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_text_found"
    assert body["resume_text"] is None
    assert row["resume_text"] is None


def test_parse_password_protected_pdf(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    row = _seed_uploaded_resume(
        fake, user_id=TEST_USER_ID, content=make_password_protected_pdf()
    )
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "password_protected"
    assert body["resume_text"] is None
    assert row["resume_text"] is None


def test_parse_does_not_clear_previous_successful_text_on_failed_reparse(
    client: TestClient, monkeypatch
) -> None:
    """A failed re-parse (e.g. the file was replaced with a bad one) must
    not erase a previous successful extraction still sitting in the DB."""

    fake = FakeClient(profiles=[])
    row = _seed_uploaded_resume(fake, user_id=TEST_USER_ID, content=b"corrupt now")
    row["resume_text"] = "previously extracted text"
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client)

    assert response.status_code == 200
    assert response.json()["status"] == "corrupt"
    assert row["resume_text"] == "previously extracted text"


def test_parse_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/profile/resume/parse")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_parse_404_when_no_profile_row(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    _patch_client(monkeypatch, fake)

    response = _parse(client)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"


def test_parse_404_when_no_resume_uploaded_yet(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[make_profile_row()])  # resume_url is None by default
    _patch_client(monkeypatch, fake)

    response = _parse(client)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESUME_NOT_FOUND"


def test_cross_user_cannot_parse_or_read_another_users_resume(
    client: TestClient, monkeypatch
) -> None:
    """Cross-user isolation: the profile row and storage path touched
    always come from the caller's own JWT."""

    fake = FakeClient(profiles=[])
    row_a = _seed_uploaded_resume(
        fake, user_id=TEST_USER_ID, content=make_pdf_with_text("A's resume")
    )
    row_b = _seed_uploaded_resume(
        fake, user_id=TEST_USER_ID_B, content=make_pdf_with_text("B's resume")
    )
    _patch_client(monkeypatch, fake)
    install_fake_storage_downloads(monkeypatch, fake.storage)

    response = _parse(client, sub=TEST_USER_ID_B)

    assert response.status_code == 200
    assert "B's resume" in response.json()["resume_text"]
    assert row_b["resume_text"] is not None
    # User A's row must be completely untouched by User B's parse call.
    assert row_a["resume_text"] is None
