"""Workable public job board scraper.

Workable exposes a public, no-auth widget JSON API:
`GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true`
-- confirmed live before writing this file (`curl` against Zego's live
board: 200, `{"name": "Zego", "description": ..., "jobs": [...]}`, 24
listings, one call, no pagination; an unknown account 404s). `details=true`
is required -- confirmed by comparing the same request with and without
it: without it, every job in `jobs[]` omits the `description` field
entirely. Like Greenhouse's `{"jobs": [...]}` envelope, not Lever's bare
array -- structurally the two aren't interchangeable despite both being
"one JSON object with a jobs list" at a glance.

## robots.txt

`apply.workable.com/robots.txt` states an empty `Disallow:` (nothing
restricted) and no crawl-delay. `rate_limit_seconds` defaults to 0.5s --
the most permissive default of the three ATS scrapers in this commit,
reflecting what this source's own robots.txt actually states rather than
being copy-pasted from Greenhouse or Lever.

## Fields Commit 11's schema can't represent

`telecommuting: true` is folded into `location` as a `"(Remote)"` suffix
-- same reasoning as `LeverScraper`'s `workplaceType` folding. Discarded:
`employment_type`, `department`, `experience`, `function`, `industry`,
`education`, the multi-entry `locations[]` array (the primary
`city`/`state`/`country` fields already capture the main location) -- see
docs/superpowers/specs/2026-07-02-ats-scrapers-design.md for the full
mapping table. `stack_tags` stays `[]` -- no skills/tags field.

`company` always comes from `app/scrapers/config/boards.json`, even
though Workable's response includes a top-level account `name` -- kept
uniform with `GreenhouseScraper`/`LeverScraper` rather than trusting the
API for two sources and config for the third.

## Multi-company partial failure

Same per-company skip-and-continue / all-fail-raises contract as
`GreenhouseScraper`/`LeverScraper` -- see those modules' docstrings, the
extension note in `app/scrapers/base.py`'s module docstring, and the
design doc. A company with zero current openings (`{"jobs": []}`) is not
a failure -- it's included in the result with an empty listing set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.config.loader import CompanyConfig, load_companies
from app.scrapers.schemas import NormalizedJob

_API_URL_TEMPLATE = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
_USER_AGENT = "KortexBot/1.0 (+https://kortex.example; job board aggregator)"


class WorkableScraper(BaseScraper):
    source_board = "workable"

    def __init__(
        self,
        *,
        companies: list[CompanyConfig] | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limit_seconds: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_base_seconds=backoff_base_seconds,
            rate_limit_seconds=rate_limit_seconds,
            headers={"User-Agent": _USER_AGENT},
            transport=transport,
        )
        self.companies = companies if companies is not None else load_companies("workable")

    async def fetch(self) -> dict[str, list[Any]]:
        raw: dict[str, list[Any]] = {}
        for company in self.companies:
            url = _API_URL_TEMPLATE.format(slug=company.slug)
            try:
                response = await self.http.get(url, params={"details": "true"})
            except httpx.HTTPError as exc:
                self.logger.warning("skipping workable company %r: %s", company.slug, exc)
                continue

            try:
                data = response.json()
            except ValueError as exc:
                self.logger.warning(
                    "skipping workable company %r: response was not valid JSON: %s",
                    company.slug,
                    exc,
                )
                continue

            jobs = data.get("jobs") if isinstance(data, dict) else None
            if not isinstance(jobs, list):
                self.logger.warning(
                    "skipping workable company %r: unexpected response shape", company.slug
                )
                continue

            raw[company.slug] = jobs

        if not raw and self.companies:
            raise ScraperError("all configured workable companies failed to fetch")

        return raw

    def parse(self, raw: dict[str, list[Any]]) -> list[NormalizedJob]:
        company_by_slug = {c.slug: c.company for c in self.companies}
        jobs: list[NormalizedJob] = []
        for slug, listings in raw.items():
            company_name = company_by_slug.get(slug, slug)
            for item in listings:
                try:
                    jobs.append(self._parse_one(item, company_name))
                except (KeyError, ValueError) as exc:
                    self.logger.warning(
                        "skipping unparsable workable listing shortcode=%r for %r: %s",
                        item.get("shortcode") if isinstance(item, dict) else None,
                        slug,
                        exc,
                    )
        return jobs

    def _parse_one(self, item: dict[str, Any], company_name: str) -> NormalizedJob:
        location_parts = [
            p for p in (item.get("city"), item.get("state"), item.get("country")) if p
        ]
        location = ", ".join(location_parts) or None
        if item.get("telecommuting"):
            location = f"{location} (Remote)" if location else "(Remote)"

        posted_at = None
        if item.get("published_on"):
            posted_at = datetime.fromisoformat(item["published_on"])

        return NormalizedJob(
            source_board=self.source_board,
            external_id=item["shortcode"],
            title=item["title"],
            company=company_name,
            location=location,
            description=item["description"],
            apply_url=item["application_url"],
            posted_at=posted_at,
        )
