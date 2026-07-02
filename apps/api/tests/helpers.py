"""Shared test helpers."""

from __future__ import annotations

import time

import jwt

TEST_JWT_SECRET = "test-jwt-secret-not-a-real-secret"
TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


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
