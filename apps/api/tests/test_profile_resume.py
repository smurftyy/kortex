"""Tests for POST /api/v1/profile/resume."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fakes import FakeClient
from tests.helpers import TEST_USER_ID, TEST_USER_ID_B, make_profile_row, make_token

VALID_PDF = b"%PDF-1.4\n%mock pdf content for tests\n%%EOF"


def _patch_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client(access_token: str):
        return fake

    monkeypatch.setattr("app.api.routes.profile.get_user_scoped_client", fake_get_client)


def test_upload_resume_success(client: TestClient, monkeypatch) -> None:
    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", VALID_PDF, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resume_url"].startswith("https://fake.storage/resumes/")

    # profiles.resume_url is updated to the stable path, not the signed URL.
    assert row["resume_url"] == f"{TEST_USER_ID}/resume.pdf"
    # Object actually landed in the private bucket at {user_id}/resume.pdf.
    assert fake.storage.objects[("resumes", f"{TEST_USER_ID}/resume.pdf")] == VALID_PDF


def test_upload_resume_wrong_content_type_rejected(client: TestClient, monkeypatch) -> None:
    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RESUME_INVALID_TYPE"
    assert fake.storage.objects == {}


def test_upload_resume_spoofed_content_type_rejected(client: TestClient, monkeypatch) -> None:
    """A client can label anything as application/pdf; the magic-byte check
    is what actually enforces PDF-only, independent of the header."""

    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RESUME_INVALID_TYPE"
    assert fake.storage.objects == {}


def test_upload_resume_oversized_rejected(client: TestClient, monkeypatch) -> None:
    row = make_profile_row()
    fake = FakeClient(profiles=[row])
    _patch_client(monkeypatch, fake)

    oversized = VALID_PDF + b"0" * (5 * 1024 * 1024)

    token = make_token()
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", oversized, "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RESUME_TOO_LARGE"
    assert fake.storage.objects == {}


def test_upload_resume_without_token_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/profile/resume",
        files={"file": ("resume.pdf", VALID_PDF, "application/pdf")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_upload_resume_404_when_no_profile_row(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(profiles=[])
    _patch_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.pdf", VALID_PDF, "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFILE_NOT_FOUND"
    assert fake.storage.objects == {}


def test_cross_user_cannot_overwrite_another_users_resume(client: TestClient, monkeypatch) -> None:
    """Cross-user isolation: the path/row touched always comes from the
    caller's own JWT, never anything client-supplied."""

    row_a = make_profile_row(user_id=TEST_USER_ID, full_name="User A")
    row_b = make_profile_row(user_id=TEST_USER_ID_B, full_name="User B")
    fake = FakeClient(profiles=[row_a, row_b])
    _patch_client(monkeypatch, fake)

    token_b = make_token(sub=TEST_USER_ID_B)
    response = client.post(
        "/api/v1/profile/resume",
        headers={"Authorization": f"Bearer {token_b}"},
        files={"file": ("resume.pdf", VALID_PDF, "application/pdf")},
    )

    assert response.status_code == 200
    assert row_b["resume_url"] == f"{TEST_USER_ID_B}/resume.pdf"
    # User A's row and storage object must be untouched by B's upload.
    assert row_a["resume_url"] is None
    assert ("resumes", f"{TEST_USER_ID}/resume.pdf") not in fake.storage.objects
