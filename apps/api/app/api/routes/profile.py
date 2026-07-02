"""Profile routes (see API_CONTRACT_kortex.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_access_token, get_current_user
from app.core.security import TokenUser
from app.core.supabase import get_user_scoped_client
from app.schemas.errors import ErrorResponse, error_body
from app.schemas.profile import ProfileResponse, ProfileUpdate, ResumeUploadResponse

router = APIRouter(prefix="/profile", tags=["profile"])

_MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5MB, per API_CONTRACT_kortex.md
_RESUME_SIGNED_URL_TTL_SECONDS = 3600
_PDF_MAGIC = b"%PDF-"


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

    if not rows or not isinstance(rows[0], dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("PROFILE_NOT_FOUND", "This account has no profile yet."),
        )

    return ProfileResponse(**rows[0])


@router.post(
    "/resume",
    response_model=ResumeUploadResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
        404: {"model": ErrorResponse, "description": "No profile row yet"},
        422: {"model": ErrorResponse, "description": "Invalid file type or size"},
    },
)
async def upload_resume(
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
    file: Annotated[UploadFile, File()],
) -> ResumeUploadResponse:
    """Upload the caller's resume (PDF only, max 5MB) to Storage.

    Does not parse the file — extracting `resume_text` is Commit 8
    (PyMuPDF), a separate concern. Rejects the wrong file type or an
    oversized file with 422 before any storage I/O happens, so a bad
    upload never reaches the storage layer at all.

    Stored at `{user_id}/resume.pdf` in the private `resumes` bucket
    (upsert — a re-upload overwrites the previous one), via a client scoped
    to the caller's own access token so Storage RLS restricts writes to
    their own `{user_id}/` prefix — never the service role key.
    """

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error_body("RESUME_INVALID_TYPE", "Resume must be a PDF file.", field="file"),
        )

    content = await file.read()

    if len(content) > _MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error_body("RESUME_TOO_LARGE", "Resume must be 5MB or smaller.", field="file"),
        )

    if not content.startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=error_body("RESUME_INVALID_TYPE", "Resume must be a PDF file.", field="file"),
        )

    client = await get_user_scoped_client(access_token)

    existing = (
        await client.table("profiles").select("id").eq("id", user.id).maybe_single().execute()
    )
    if existing is None or not isinstance(existing.data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("PROFILE_NOT_FOUND", "This account has no profile yet."),
        )

    path = f"{user.id}/resume.pdf"
    await client.storage.from_("resumes").upload(
        path, content, {"content-type": "application/pdf", "upsert": "true"}
    )

    signed = await client.storage.from_("resumes").create_signed_url(
        path, _RESUME_SIGNED_URL_TTL_SECONDS
    )
    signed_url = signed.get("signedURL") or signed.get("signedUrl")
    assert signed_url is not None

    await client.table("profiles").update(
        {"resume_url": path, "updated_at": datetime.now(UTC).isoformat()}
    ).eq("id", user.id).execute()

    return ResumeUploadResponse(resume_url=signed_url)
