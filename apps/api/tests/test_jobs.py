"""Tests for /api/v1/jobs and the job_matches status-transition actions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fakes import FakeClient
from tests.helpers import (
    TEST_JOB_ID,
    TEST_USER_ID,
    TEST_USER_ID_B,
    make_job_match_row,
    make_job_row,
    make_token,
)


def _patch_anon_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client():
        return fake

    monkeypatch.setattr("app.api.routes.jobs.get_anon_client", fake_get_client)


def _patch_user_client(monkeypatch, fake: FakeClient) -> None:
    async def fake_get_client(access_token: str):
        return fake

    monkeypatch.setattr("app.api.routes.jobs.get_user_scoped_client", fake_get_client)


# --- GET /jobs -------------------------------------------------------------


def test_list_jobs_is_public_no_token_required(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(jobs=[make_job_row()])
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["results"][0]["job_id"] == TEST_JOB_ID


def test_list_jobs_excludes_inactive_by_default(client: TestClient, monkeypatch) -> None:
    active = make_job_row(job_id=TEST_JOB_ID, is_active=True)
    inactive = make_job_row(job_id="99999999-9999-9999-9999-999999999999", is_active=False)
    fake = FakeClient(jobs=[active, inactive])
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [r["job_id"] for r in body["results"]] == [TEST_JOB_ID]


def test_list_jobs_filters_by_board(client: TestClient, monkeypatch) -> None:
    greenhouse = make_job_row(job_id=TEST_JOB_ID, source_board="greenhouse")
    lever = make_job_row(job_id="88888888-8888-8888-8888-888888888888", source_board="lever")
    fake = FakeClient(jobs=[greenhouse, lever])
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs", params={"board": "lever"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["source_board"] == "lever"


def test_list_jobs_filters_by_location_partial_match(client: TestClient, monkeypatch) -> None:
    lagos = make_job_row(job_id=TEST_JOB_ID, location="Lagos, Nigeria")
    remote = make_job_row(job_id="77777777-7777-7777-7777-777777777777", location="Remote")
    fake = FakeClient(jobs=[lagos, remote])
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs", params={"location": "lagos"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["location"] == "Lagos, Nigeria"


def test_list_jobs_filters_by_stack_tag(client: TestClient, monkeypatch) -> None:
    py_job = make_job_row(job_id=TEST_JOB_ID, stack_tags=["Python", "FastAPI"])
    go_job = make_job_row(job_id="66666666-6666-6666-6666-666666666666", stack_tags=["Go"])
    fake = FakeClient(jobs=[py_job, go_job])
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs", params={"stack": "Python"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["job_id"] == TEST_JOB_ID


def test_list_jobs_paginates(client: TestClient, monkeypatch) -> None:
    rows = [make_job_row(job_id=f"a0000000-0000-0000-0000-00000000000{i}") for i in range(3)]
    fake = FakeClient(jobs=rows)
    _patch_anon_client(monkeypatch, fake)

    response = client.get("/api/v1/jobs", params={"page": 1, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["results"]) == 2
    assert body["page_size"] == 2


# --- GET /jobs/{id} ----------------------------------------------------------


def test_get_job_returns_detail(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(jobs=[make_job_row()])
    _patch_anon_client(monkeypatch, fake)

    response = client.get(f"/api/v1/jobs/{TEST_JOB_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == TEST_JOB_ID
    assert body["description"] == "A great opportunity."


def test_get_job_404_when_nonexistent(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(jobs=[])
    _patch_anon_client(monkeypatch, fake)

    response = client.get(f"/api/v1/jobs/{TEST_JOB_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_get_job_404_when_inactive(client: TestClient, monkeypatch) -> None:
    fake = FakeClient(jobs=[make_job_row(is_active=False)])
    _patch_anon_client(monkeypatch, fake)

    response = client.get(f"/api/v1/jobs/{TEST_JOB_ID}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


# --- POST /jobs/{id}/{approve,skip,save} ------------------------------------


def test_approve_job_success(client: TestClient, monkeypatch) -> None:
    match = make_job_match_row(user_id=TEST_USER_ID, job_id=TEST_JOB_ID, match_status="new")
    fake = FakeClient(job_matches=[match])
    _patch_user_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/approve", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204
    assert match["status"] == "approved"


def test_skip_job_success(client: TestClient, monkeypatch) -> None:
    match = make_job_match_row(user_id=TEST_USER_ID, job_id=TEST_JOB_ID, match_status="new")
    fake = FakeClient(job_matches=[match])
    _patch_user_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/skip", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204
    assert match["status"] == "skipped"


def test_save_job_success(client: TestClient, monkeypatch) -> None:
    match = make_job_match_row(user_id=TEST_USER_ID, job_id=TEST_JOB_ID, match_status="new")
    fake = FakeClient(job_matches=[match])
    _patch_user_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/save", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 204
    assert match["status"] == "saved"


def test_approve_job_without_token_returns_401(client: TestClient) -> None:
    response = client.post(f"/api/v1/jobs/{TEST_JOB_ID}/approve")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_approve_job_404_when_job_does_not_exist(client: TestClient, monkeypatch) -> None:
    """No job_matches row can reference a nonexistent job, so this collapses
    to the same 404 as "job exists but no match row" — see the module
    docstring in app/api/routes/jobs.py."""

    fake = FakeClient(job_matches=[])
    _patch_user_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/approve", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_NOT_FOUND"


def test_approve_job_404_when_job_exists_but_no_match_row(client: TestClient, monkeypatch) -> None:
    # job_matches is empty even though the job itself would exist elsewhere;
    # from the route's perspective (it never queries `jobs`) this is
    # identical to the nonexistent-job case above.
    fake = FakeClient(job_matches=[])
    _patch_user_client(monkeypatch, fake)

    token = make_token()
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/approve", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_NOT_FOUND"


def test_cross_user_cannot_approve_another_users_match(client: TestClient, monkeypatch) -> None:
    """Cross-user isolation: POST actions always filter by the caller's own JWT id."""

    match_a = make_job_match_row(user_id=TEST_USER_ID, job_id=TEST_JOB_ID, match_status="new")
    fake = FakeClient(job_matches=[match_a])
    _patch_user_client(monkeypatch, fake)

    token_b = make_token(sub=TEST_USER_ID_B)
    response = client.post(
        f"/api/v1/jobs/{TEST_JOB_ID}/approve", headers={"Authorization": f"Bearer {token_b}"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MATCH_NOT_FOUND"
    # User A's row must be untouched by User B's attempt.
    assert match_a["status"] == "new"
