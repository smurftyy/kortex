"""Jobs routes (see API_CONTRACT_kortex.md).

`GET /jobs` and `GET /jobs/{job_id}` are public reads of the `jobs` table —
no RLS on that table (SCHEMA_kortex.md section 4) and no authentication
required (see `JWTAuthMiddleware`'s `_PUBLIC_GET_PATTERNS`). The three
action endpoints below require the caller's JWT and only ever UPDATE an
existing `job_matches` row scoped to that user via RLS — they never create
one, since `job_matches` has no INSERT policy (locked decision, Commit 5).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from postgrest.types import CountMethod

from app.api.deps import get_access_token, get_current_user
from app.core.security import TokenUser
from app.core.supabase import get_anon_client, get_user_scoped_client
from app.schemas.errors import ErrorResponse, error_body
from app.schemas.job import JobDetail, JobListItem, JobListResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_MAX_PAGE_SIZE = 100


def _to_list_item(row: dict) -> JobListItem:
    return JobListItem(
        job_id=row["id"],
        title=row["title"],
        company=row["company"],
        location=row.get("location"),
        stack_tags=row.get("stack_tags", []),
        source_board=row["source_board"],
        posted_at=row.get("posted_at"),
        discovered_at=row["discovered_at"],
    )


def _to_detail(row: dict) -> JobDetail:
    return JobDetail(
        job_id=row["id"],
        title=row["title"],
        company=row["company"],
        location=row.get("location"),
        description=row["description"],
        stack_tags=row.get("stack_tags", []),
        apply_url=row["apply_url"],
        source_board=row["source_board"],
        posted_at=row.get("posted_at"),
        discovered_at=row["discovered_at"],
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    board: Annotated[str | None, Query(description="Filter by source_board")] = None,
    location: Annotated[str | None, Query(description="Case-insensitive partial match")] = None,
    stack: Annotated[str | None, Query(description="Filter by a single stack tag")] = None,
    date_from: Annotated[datetime | None, Query(description="posted_at lower bound")] = None,
    date_to: Annotated[datetime | None, Query(description="posted_at upper bound")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=_MAX_PAGE_SIZE)] = 20,
) -> JobListResponse:
    """List active jobs, filtered and paginated. Public — no auth required."""

    client = await get_anon_client()
    query = client.table("jobs").select("*", count=CountMethod.exact).eq("is_active", True)

    if board:
        query = query.eq("source_board", board)
    if location:
        query = query.ilike("location", f"%{location}%")
    if stack:
        query = query.contains("stack_tags", [stack])
    if date_from:
        query = query.gte("posted_at", date_from.isoformat())
    if date_to:
        query = query.lte("posted_at", date_to.isoformat())

    offset = (page - 1) * page_size
    result = (
        await query.order("discovered_at", desc=True).limit(page_size).offset(offset).execute()
    )
    rows = result.data if isinstance(result.data, list) else []

    return JobListResponse(
        results=[_to_list_item(row) for row in rows if isinstance(row, dict)],
        page=page,
        page_size=page_size,
        total=result.count or 0,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetail,
    responses={404: {"model": ErrorResponse, "description": "Job not found or inactive"}},
)
async def get_job(job_id: UUID) -> JobDetail:
    """Return a single active job. Public — no auth required.

    404 for both a nonexistent id and a soft-deleted one (`is_active =
    false`) — a closed listing shouldn't be individually fetchable even
    though it may still be referenced by a user's match history.
    """

    client = await get_anon_client()
    result = (
        await client.table("jobs")
        .select("*")
        .eq("id", str(job_id))
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )

    if result is None or not isinstance(result.data, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("JOB_NOT_FOUND", "This job does not exist or is no longer active."),
        )

    return _to_detail(result.data)


async def _transition_match_status(
    job_id: UUID, new_status: str, user: TokenUser, access_token: str
) -> None:
    """UPDATE-only status transition for the caller's own job_matches row.

    Never creates a row: `job_matches` has no INSERT policy, so a caller
    with no existing match for this job gets 404, by design.
    """

    client = await get_user_scoped_client(access_token)
    result = (
        await client.table("job_matches")
        .update({"status": new_status})
        .eq("job_id", str(job_id))
        .eq("user_id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_body("MATCH_NOT_FOUND", "No match record exists for this job."),
        )


_ACTION_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    404: {"model": ErrorResponse, "description": "No match record for this job"},
}


@router.post(
    "/{job_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ACTION_RESPONSES,
)
async def approve_job(
    job_id: UUID,
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> None:
    await _transition_match_status(job_id, "approved", user, access_token)


@router.post("/{job_id}/skip", status_code=status.HTTP_204_NO_CONTENT, responses=_ACTION_RESPONSES)
async def skip_job(
    job_id: UUID,
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> None:
    await _transition_match_status(job_id, "skipped", user, access_token)


@router.post("/{job_id}/save", status_code=status.HTTP_204_NO_CONTENT, responses=_ACTION_RESPONSES)
async def save_job(
    job_id: UUID,
    user: Annotated[TokenUser, Depends(get_current_user)],
    access_token: Annotated[str, Depends(get_access_token)],
) -> None:
    await _transition_match_status(job_id, "saved", user, access_token)
