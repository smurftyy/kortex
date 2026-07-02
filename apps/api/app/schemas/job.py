"""Pydantic schemas for the jobs resource (see SCHEMA_kortex.md section 4).

`match_score`/`status`/`score_breakdown` from API_CONTRACT_kortex.md's
original sketch are per-user `job_matches` fields and are intentionally
omitted here — `GET /jobs` and `GET /jobs/{job_id}` are public,
unauthenticated reads (see Commit 6), so there is no caller to scope a match
to. The contract doc is updated alongside this commit to reflect that.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobListItem(BaseModel):
    job_id: UUID
    title: str
    company: str
    location: str | None = None
    stack_tags: list[str]
    source_board: str
    posted_at: datetime | None = None
    discovered_at: datetime


class JobListResponse(BaseModel):
    results: list[JobListItem]
    page: int
    page_size: int
    total: int


class JobDetail(BaseModel):
    job_id: UUID
    title: str
    company: str
    location: str | None = None
    description: str
    stack_tags: list[str]
    apply_url: str
    source_board: str
    posted_at: datetime | None = None
    discovered_at: datetime
