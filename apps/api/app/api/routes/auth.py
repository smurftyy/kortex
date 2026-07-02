"""Auth-related routes (see API_CONTRACT_kortex.md)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_access_token, get_current_user
from app.core.security import TokenUser
from app.core.supabase import get_user_scoped_client
from app.schemas.errors import ErrorResponse, error_body
from app.schemas.profile import ProfileResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/me",
    response_model=ProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        404: {"model": ErrorResponse, "description": "No profile row yet"},
    },
)
async def get_me(
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> ProfileResponse:
    """Return the caller's own profile row.

    Queried through a client scoped to the caller's own access token, so the
    `profiles` RLS policy (``auth.uid() = id``) is what actually restricts
    the row returned, not an application-level filter.
    """

    client = await get_user_scoped_client(access_token)
    result = await client.table("profiles").select("*").eq("id", user.id).maybe_single().execute()

    if result is None or not isinstance(result.data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body(
                "PROFILE_NOT_FOUND",
                "This account has no profile yet.",
            ),
        )

    return ProfileResponse(**result.data)
