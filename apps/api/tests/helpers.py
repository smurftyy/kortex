"""Shared test helpers."""

from __future__ import annotations

import time
import uuid

import jwt

TEST_JWT_SECRET = "test-jwt-secret-not-a-real-secret"
TEST_USER_ID = "11111111-1111-1111-1111-111111111111"
TEST_USER_ID_B = "22222222-2222-2222-2222-222222222222"


def make_profile_row(*, user_id: str = TEST_USER_ID, full_name: str = "Ada Lovelace") -> dict:
    return {
        "id": user_id,
        "full_name": full_name,
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


def make_preferences_row(*, user_id: str = TEST_USER_ID) -> dict:
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"prefs-{user_id}")),
        "user_id": user_id,
        "boards_enabled": ["greenhouse", "lever"],
        "location_filter": ["remote"],
        "excluded_keywords": [],
        "digest_time_local": "08:00:00",
        "digest_timezone": "Africa/Lagos",
        "match_score_threshold": 2.0,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


TEST_JOB_ID = "33333333-3333-3333-3333-333333333333"


def make_job_row(
    *,
    job_id: str = TEST_JOB_ID,
    title: str = "Backend Intern",
    company: str = "Acme",
    source_board: str = "greenhouse",
    location: str = "Lagos, Nigeria",
    stack_tags: list[str] | None = None,
    is_active: bool = True,
    posted_at: str | None = "2026-01-01T00:00:00+00:00",
) -> dict:
    return {
        "id": job_id,
        "source_board": source_board,
        "external_id": None,
        "title": title,
        "company": company,
        "location": location,
        "description": "A great opportunity.",
        "stack_tags": stack_tags if stack_tags is not None else ["Python"],
        "apply_url": "https://example.com/apply",
        "dedup_hash": f"hash-{job_id}",
        "posted_at": posted_at,
        "discovered_at": "2026-01-02T00:00:00+00:00",
        "is_active": is_active,
    }


def make_job_match_row(
    *,
    user_id: str = TEST_USER_ID,
    job_id: str = TEST_JOB_ID,
    match_status: str = "new",
    match_score: float = 7.5,
) -> dict:
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"match-{user_id}-{job_id}")),
        "user_id": user_id,
        "job_id": job_id,
        "match_score": match_score,
        "score_breakdown": {"skill_match": match_score},
        "status": match_status,
        "notified_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def make_token(
    *,
    sub: str = TEST_USER_ID,
    email: str = "person@example.com",
    role: str = "authenticated",
    expired: bool = False,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Mint a Supabase-shaped access token for tests."""

    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "role": role,
        "aud": "authenticated",
        "iat": now - 10,
        "exp": now - 5 if expired else now + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
