"""Normalized scraper output contract (see SCHEMA_kortex.md section 4).

Every scraper's `parse()` (Commits 12-14) must return `NormalizedJob`
instances. Fields map 1:1 onto real `jobs` columns, confirmed against the
Commit 5 migration — with three deliberate exclusions:

- `dedup_hash` — Commit 15 computes this from `apply_url` + `title` +
  `company` (see the migration's own comment: `hash(url + title + company)`
  ). Those three source fields are all present below; the hash itself is
  not this commit's job to produce.
- `discovered_at` — `TIMESTAMPTZ NOT NULL DEFAULT now()` at the DB layer.
  It records when *our system* inserted the row, not anything the source
  reports — a scraper has no meaningful value to supply for it.
- `is_active` — `BOOLEAN NOT NULL DEFAULT true`. Determining a listing has
  gone stale requires comparing across scrape runs over time, which a
  single fetch -> parse pass can't determine on its own; that's later
  lifecycle-management logic, not part of a single normalized result.
- `id` — server-generated (`gen_random_uuid()`); a scraper never assigns
  primary keys.

`BoardSource`'s seven values come from `preferences.boards_enabled`'s
DEFAULT array (Commit 2 migration / SCHEMA_kortex.md section 3) — the only
place in the schema docs that actually enumerates every supported board,
and it matches this project's "7 scrapers downstream" (Commits 12-14).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

BoardSource = Literal[
    "greenhouse",
    "lever",
    "workable",
    "remoteok",
    "web3career",
    "cryptojobslist",
    "linkedin",
]


class NormalizedJob(BaseModel):
    """One listing, normalized to the `jobs` table's shape.

    `source_board` is `Literal`-typed (not `str`) so a scraper typo'ing a
    board name fails at schema validation, not silently at DB insert time.
    """

    model_config = ConfigDict(extra="forbid")

    source_board: BoardSource
    external_id: str | None = None
    title: str
    company: str
    location: str | None = None
    description: str
    stack_tags: list[str] = Field(default_factory=list)
    apply_url: str
    posted_at: datetime | None = None

    @field_validator("apply_url")
    @classmethod
    def _apply_url_looks_like_a_url(cls, value: str) -> str:
        # Deliberately not pydantic's `HttpUrl` type: that normalizes the
        # string (e.g. adds a trailing slash), which would make the same
        # listing hash differently across scrapers depending on whether
        # normalization happened to change anything — `apply_url` feeds
        # directly into Commit 15's dedup hash, so it must stay exactly
        # what the source returned. This only rejects the obviously wrong.
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("apply_url must be an absolute http(s) URL")
        return value
