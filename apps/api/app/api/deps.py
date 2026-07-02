"""Shared FastAPI dependencies for routes protected by JWTAuthMiddleware."""

from __future__ import annotations

from fastapi import Request

from app.core.security import TokenUser


def get_current_user(request: Request) -> TokenUser:
    """Return the identity attached by :class:`JWTAuthMiddleware`."""

    return request.state.user


def get_access_token(request: Request) -> str:
    """Return the raw bearer token attached by :class:`JWTAuthMiddleware`."""

    return request.state.access_token
