"""Pydantic schema for the profiles resource (see SCHEMA_kortex.md section 2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


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
