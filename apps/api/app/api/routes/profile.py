"""Profile routes (see API_CONTRACT_kortex.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_access_token, get_current_user
from app.core.security import TokenUser
from app.core.supabase import get_user_scoped_client
from app.schemas.errors import ErrorResponse, error_body
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.patch(
    "",
    response_model=ProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        404: {"model": ErrorResponse, "description": "No profile row yet"},
        422: {"model": ErrorResponse, "description": "Validation failure"},
    },
)
async def patch_profile(
    payload: ProfileUpdate,
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> ProfileResponse:
    """Partially update the caller's own profile row.

    Only fields present in the request body are changed. The write goes
    through a client scoped to the caller's own access token, so `profiles`
    RLS (``auth.uid() = id``) is what restricts it to their own row — there
    is no `service_role` key on this path.
    """

    client = await get_user_scoped_client(access_token)
    updates = payload.model_dump(exclude_unset=True, mode="json")

    if updates:
        updates["updated_at"] = datetime.now(UTC).isoformat()
        result = await client.table("profiles").update(updates).eq("id", user.id).execute()
        rows = result.data
    else:
        fetched = (
            await client.table("profiles").select("*").eq("id", user.id).maybe_single().execute()
        )
        rows = [fetched.data] if fetched is not None and isinstance(fetched.data, dict) else []

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("PROFILE_NOT_FOUND", "This account has no profile yet."),
        )

    return ProfileResponse(**rows[0])
