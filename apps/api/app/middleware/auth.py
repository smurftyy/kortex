"""ASGI middleware that authenticates Supabase JWTs on protected routes."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import decode_access_token
from app.schemas.errors import error_body

PUBLIC_PATHS = frozenset(
    {
        "/health",
        "/api/v1/auth/signup",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

# `jobs` has no RLS (public read; see SCHEMA_kortex.md section 4), so its
# list/detail GETs skip auth entirely. Scoped to GET + a single path segment
# so `POST /jobs/{id}/approve|skip|save` (which do require auth) never match.
_PUBLIC_GET_PATTERNS = (
    re.compile(r"^/api/v1/jobs$"),
    re.compile(r"^/api/v1/jobs/[^/]+$"),
)

_UNAUTHORIZED_MESSAGE = "Missing or invalid authentication token."


def _is_public(request: Request) -> bool:
    if request.url.path in PUBLIC_PATHS:
        return True
    if request.method == "GET":
        return any(pattern.match(request.url.path) for pattern in _PUBLIC_GET_PATTERNS)
    return False


def _unauthorized() -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_body("UNAUTHORIZED", _UNAUTHORIZED_MESSAGE),
        headers={"WWW-Authenticate": "Bearer"},
    )


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Verifies the caller's Supabase access token on every non-public route.

    On success, the decoded identity and raw token are attached to
    ``request.state`` for downstream dependencies. Every verification
    failure (missing header, malformed token, bad signature, expiry)
    collapses into the same generic 401 body — the client never learns
    which check failed.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if _is_public(request):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return _unauthorized()

        try:
            user = decode_access_token(token)
        except jwt.InvalidTokenError:
            return _unauthorized()

        request.state.user = user
        request.state.access_token = token
        return await call_next(request)
