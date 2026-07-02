"""Shared config-file loader for per-source company/board lists.

Company lists live in `boards.json` (this directory), not env vars or a DB
table — adding a company is a JSON edit + normal PR, no migration, no new
admin UI. See docs/superpowers/specs/2026-07-02-ats-scrapers-design.md for
the full reasoning; this loader is the one implementation Commits 12-14
all share.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import get_args

from pydantic import BaseModel, ConfigDict, field_validator

from app.scrapers.base import ScraperError
from app.scrapers.schemas import BoardSource

_DEFAULT_CONFIG_PATH = Path(__file__).parent / "boards.json"
_VALID_SOURCES = get_args(BoardSource)


class ConfigLoadError(ScraperError):
    """`boards.json` itself is missing, malformed, or shaped wrong for the
    requested source -- a deployment/config error, not a per-entry data
    problem. A single company's own bad entry (missing/blank field,
    unexpected field) stays a plain pydantic `ValidationError`: that's a
    data-quality issue in one config row, not evidence the file itself is
    broken.
    """


class CompanyConfig(BaseModel):
    """One company/board entry for a given source.

    `company` is always config-supplied, even for sources (Greenhouse,
    Workable) whose API response includes its own company name — kept
    uniform across all three sources rather than trusting the API for two
    of them and requiring config only for the third (Lever has no
    company-name field at all). See the design doc's field-mapping
    section for the full reasoning.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    company: str

    @field_validator("slug", "company")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        # Deliberately not normalizing (e.g. via .strip()) the stored
        # value -- matches NormalizedJob.apply_url's precedent in
        # schemas.py: this only rejects the obviously wrong, so slug/
        # company stay exactly what boards.json says.
        if not value.strip():
            raise ValueError("must not be blank")
        return value


def load_companies(source: BoardSource, *, path: Path | None = None) -> list[CompanyConfig]:
    """Load the configured companies for one source (e.g. "greenhouse").

    Returns an empty list if the source has no entries in the config file.

    Raises `ConfigLoadError` for anything wrong with the config file
    itself -- an unrecognized `source`, a missing/unreadable file, invalid
    JSON, a source's value shaped wrong (not a list, or containing
    non-object items), or a duplicate `slug` within one source's list --
    since those are deployment/config errors, not a per-source runtime
    condition to swallow. Raises `pydantic.ValidationError` for a single
    malformed company entry (missing/blank field, unexpected field): that
    is a data problem in one row, distinct from the file itself being
    broken.
    """

    if source not in _VALID_SOURCES:
        raise ConfigLoadError(
            f"unknown source board {source!r}; expected one of {_VALID_SOURCES}"
        )

    config_path = path or _DEFAULT_CONFIG_PATH

    try:
        raw_text = config_path.read_text()
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"config file not found: {config_path}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(f"config file is not valid JSON: {config_path}") from exc

    entries = data.get(source, [])

    companies: list[CompanyConfig] = []
    seen_slugs: set[str] = set()
    try:
        for entry in entries:
            company = CompanyConfig(**entry)
            if company.slug in seen_slugs:
                raise ConfigLoadError(
                    f"duplicate slug {company.slug!r} configured for source {source!r}"
                )
            seen_slugs.add(company.slug)
            companies.append(company)
    except TypeError as exc:
        raise ConfigLoadError(
            f"malformed company data for source {source!r}: "
            f"expected a list of objects, got {entries!r}"
        ) from exc

    return companies
