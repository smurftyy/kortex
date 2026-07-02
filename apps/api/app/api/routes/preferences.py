"""Preferences routes (see API_CONTRACT_kortex.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_access_token, get_current_user
from app.core.security import TokenUser
from app.core.supabase import get_user_scoped_client
from app.schemas.errors import ErrorResponse, error_body
from app.schemas.preferences import PreferencesResponse, PreferencesUpsert

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get(
    "",
    response_model=PreferencesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        404: {"model": ErrorResponse, "description": "No preferences row yet"},
    },
)
async def get_preferences(
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> PreferencesResponse:
    """Return the caller's own preferences row.

    Queried through a client scoped to the caller's own access token, so
    `preferences` RLS (``auth.uid() = user_id``) restricts the row returned.
    """

    client = await get_user_scoped_client(access_token)
    result = (
        await client.table("preferences")
        .select("*")
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )

    if result is None or not isinstance(result.data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("PREFERENCES_NOT_FOUND", "This account has no preferences yet."),
        )

    return PreferencesResponse(**result.data)


@router.put(
    "",
    response_model=PreferencesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        422: {"model": ErrorResponse, "description": "Validation failure"},
    },
)
async def put_preferences(
    payload: PreferencesUpsert,
    response: Response,
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> PreferencesResponse:
    """Create or fully replace the caller's own preferences row.

    Upserts on the `user_id` unique constraint (Commit 2 migration), so a
    second call replaces rather than duplicates. `user_id` is always taken
    from the caller's own JWT, never from the request body.
    """

    client = await get_user_scoped_client(access_token)

    existing = (
        await client.table("preferences")
        .select("id")
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )
    already_existed = existing is not None and isinstance(existing.data, dict)

    body = payload.model_dump(mode="json")
    body["user_id"] = user.id
    body["updated_at"] = datetime.now(UTC).isoformat()

    result = await client.table("preferences").upsert(body, on_conflict="user_id").execute()
    row = result.data[0]
    assert isinstance(row, dict)

    response.status_code = status.HTTP_200_OK if already_existed else status.HTTP_201_CREATED
    return PreferencesResponse(**row)
