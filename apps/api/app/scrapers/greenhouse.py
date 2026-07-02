"""Greenhouse job board scraper.

Greenhouse exposes a public, no-auth JSON API for embeddable job boards:
`GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`
-- confirmed live before writing this file (`curl` against Stripe's board:
200, `{"jobs": [...], "meta": ...}`, 490 listings, one call, no pagination;
an unknown token 404s). `content=true` is required to get each listing's
HTML description inline via the `content` field; without it, `content` is
omitted from every job.

## robots.txt

`boards-api.greenhouse.io/robots.txt` disallows only `/embed/`; the
`/v1/boards/...` path used here is not restricted, and no crawl-delay is
stated. `rate_limit_seconds` defaults to 0.75s regardless -- a public
board-embed API meant for external consumption, but staying courteous
without a stated floor to work against.

## Fields Commit 11's schema can't represent

Discarded, with nothing reasonable to fold in: `departments`, `offices`,
`requisition_id`, `data_compliance`, `metadata`, `internal_job_id`,
`ai_disclaimer`/`ai_opt_out_request_url`, `language`,
`application_deadline`. `stack_tags` stays `[]` -- the board API has no
skills/tags field. See docs/superpowers/specs/
2026-07-02-ats-scrapers-design.md for the full mapping table.

## Multi-company partial failure

`fetch()` loops over every company configured for `greenhouse` in
`app/scrapers/config/boards.json`. A single company's board 404ing
(stale/renamed token), returning an unexpected response shape, or
otherwise being unreachable is logged and skipped -- extending Commit 11's
per-listing skip-and-continue contract to per-company, since each
configured company is its own independent sub-fetch, not a single listing
within one response (see the extension note in `app/scrapers/base.py`'s
module docstring). `ScraperError` is raised only if every configured
company fails. A company with zero current openings (`{"jobs": []}`) is
not a failure -- it's included in the result with an empty listing set.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.config.loader import CompanyConfig, load_companies
from app.scrapers.schemas import NormalizedJob

_API_URL_TEMPLATE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
_USER_AGENT = "KortexBot/1.0 (+https://kortex.example; job board aggregator)"


class GreenhouseScraper(BaseScraper):
    source_board = "greenhouse"

    def __init__(
        self,
        *,
        companies: list[CompanyConfig] | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limit_seconds: float = 0.75,
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
        self.companies = companies if companies is not None else load_companies("greenhouse")

    async def fetch(self) -> dict[str, list[Any]]:
        raw: dict[str, list[Any]] = {}
        for company in self.companies:
            url = _API_URL_TEMPLATE.format(token=company.slug)
            try:
                response = await self.http.get(url, params={"content": "true"})
            except httpx.HTTPError as exc:
                self.logger.warning("skipping greenhouse company %r: %s", company.slug, exc)
                continue

            try:
                data = response.json()
            except ValueError as exc:
                self.logger.warning(
                    "skipping greenhouse company %r: response was not valid JSON: %s",
                    company.slug,
                    exc,
                )
                continue

            jobs = data.get("jobs") if isinstance(data, dict) else None
            if not isinstance(jobs, list):
                self.logger.warning(
                    "skipping greenhouse company %r: unexpected response shape", company.slug
                )
                continue

            raw[company.slug] = jobs

        if not raw and self.companies:
            raise ScraperError("all configured greenhouse companies failed to fetch")

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
                        "skipping unparsable greenhouse listing id=%r for %r: %s",
                        item.get("id") if isinstance(item, dict) else None,
                        slug,
                        exc,
                    )
        return jobs

    def _parse_one(self, item: dict[str, Any], company_name: str) -> NormalizedJob:
        location = None
        loc = item.get("location")
        if isinstance(loc, dict):
            location = loc.get("name") or None

        posted_at = None
        if item.get("first_published"):
            posted_at = datetime.fromisoformat(item["first_published"])

        return NormalizedJob(
            source_board=self.source_board,
            external_id=str(item["id"]),
            title=item["title"],
            company=company_name,
            location=location,
            description=item["content"],
            apply_url=item["absolute_url"],
            posted_at=posted_at,
        )
