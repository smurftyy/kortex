"""Pydantic schema for the profiles resource (see SCHEMA_kortex.md section 2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

# Columns that are NOT NULL in the profiles table (see SCHEMA_kortex.md section
# 2). A PATCH may omit them, but may not explicitly set them to null.
_PROFILE_NOT_NULLABLE_FIELDS = ("full_name", "experience_level", "target_roles", "skills")


class ProfileResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    experience_level: Literal["intern", "junior", "mid"]
    target_roles: list[str]
    skills: list[str]
    resume_url: str | None = None
    resume_text: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    """Partial update body for ``PATCH /profile``. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    linkedin_url: str | None = None
    experience_level: Literal["intern", "junior", "mid"] | None = None
    target_roles: list[str] | None = None
    skills: list[str] | None = None

    @model_validator(mode="after")
    def _reject_null_for_required_columns(self) -> ProfileUpdate:
        for field_name in _PROFILE_NOT_NULLABLE_FIELDS:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"'{field_name}' cannot be null")
        return self


class ResumeUploadResponse(BaseModel):
    """Response for ``POST /profile/resume``.

    ``resume_url`` here is a freshly generated signed URL, immediately
    usable by the client. The value persisted to ``profiles.resume_url`` is
    the stable object path within the `resumes` bucket, not this signed URL
    — a signed URL expires and would go stale if stored directly.
    """

    resume_url: str
