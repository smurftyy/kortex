"""Pydantic schemas for the preferences resource (see SCHEMA_kortex.md section 3)."""

from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PreferencesUpsert(BaseModel):
    """Full-replace body for ``PUT /preferences``. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    boards_enabled: list[str]
    location_filter: list[str]
    excluded_keywords: list[str]
    digest_time_local: time
    digest_timezone: str
    match_score_threshold: float


class PreferencesResponse(BaseModel):
    id: UUID
    user_id: UUID
    boards_enabled: list[str]
    location_filter: list[str]
    excluded_keywords: list[str]
    digest_time_local: time
    digest_timezone: str
    match_score_threshold: float
    created_at: datetime
    updated_at: datetime
