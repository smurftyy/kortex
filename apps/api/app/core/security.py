"""JWT verification for Supabase-issued access tokens."""

from __future__ import annotations

from dataclasses import dataclass

import jwt

from app.core.config import get_settings


@dataclass(frozen=True)
class TokenUser:
    """Decoded identity claims from a verified Supabase JWT."""

    id: str
    email: str | None
    role: str | None


def decode_access_token(token: str) -> TokenUser:
    """Verify a Supabase access token and return its identity claims.

    Raises ``jwt.InvalidTokenError`` (or a subclass, e.g.
    ``ExpiredSignatureError``) on any signature, expiry, audience, or
    claim-shape failure. Callers must not surface *which* check failed —
    only that verification failed.
    """

    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )

    sub = payload.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("token missing 'sub' claim")

    return TokenUser(id=sub, email=payload.get("email"), role=payload.get("role"))
