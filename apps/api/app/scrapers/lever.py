"""Lever postings scraper.

Lever exposes a public, no-auth JSON API for embeddable job postings:
`GET https://api.lever.co/v0/postings/{slug}?mode=json` -- confirmed live
before writing this file (`curl` against Ro's live board: 200, a bare JSON
array of 57 postings, one call, no pagination; an unknown slug 404s).
Unlike Greenhouse's `{"jobs": [...]}` envelope, this endpoint returns the
array directly at the top level.

## robots.txt

`api.lever.co/robots.txt` states `Crawl-delay: 1` explicitly for all user
agents -- `rate_limit_seconds` defaults to 1.0 to honor it directly.

## Fields Commit 11's schema can't represent

Lever's top-level `description` field is only the intro paragraph; the
substantive job content (What You'll Do / requirements / benefits) lives
in a separate `lists` array of `{text, content}` HTML sections. Rather
than drop that content, it's concatenated onto `description` as
`<h3>{heading}</h3>{content}` per section. `categories.workplaceType`
(remote/hybrid/onsite) is folded into `location` as a suffix (e.g.
"New York, NY (hybrid)") for the same reason: not a `NormalizedJob`
field, but `location` is free text and losing the signal outright would
be worse than a suffix -- same approach `GreenhouseScraper`/`RemoteOKScraper`
already use for their own location cleanup. See docs/superpowers/specs/
2026-07-02-ats-scrapers-design.md for the full mapping table. Discarded:
`categories.commitment`, `country`, `additionalPlain`. `stack_tags` stays
`[]` -- `categories.team` is an org label, not a tech stack.

Lever's API has no company-name field at all -- `company` always comes
from `app/scrapers/config/boards.json`, not the response.

## Multi-company partial failure

Same per-company skip-and-continue / all-fail-raises contract as
`GreenhouseScraper` -- see that module's docstring, the extension note in
`app/scrapers/base.py`'s module docstring, and the design doc. A company
with zero current postings (`[]`) is not a failure -- it's included in the
result with an empty listing set.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.config.loader import CompanyConfig, load_companies
from app.scrapers.schemas import NormalizedJob

_API_URL_TEMPLATE = "https://api.lever.co/v0/postings/{slug}"
_USER_AGENT = "KortexBot/1.0 (+https://kortex.example; job board aggregator)"


class LeverScraper(BaseScraper):
    source_board = "lever"

    def __init__(
        self,
        *,
        companies: list[CompanyConfig] | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limit_seconds: float = 1.0,
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
        self.companies = companies if companies is not None else load_companies("lever")

    async def fetch(self) -> dict[str, list[Any]]:
        raw: dict[str, list[Any]] = {}
        for company in self.companies:
            url = _API_URL_TEMPLATE.format(slug=company.slug)
            try:
                response = await self.http.get(url, params={"mode": "json"})
            except httpx.HTTPError as exc:
                self.logger.warning("skipping lever company %r: %s", company.slug, exc)
                continue

            try:
                data = response.json()
            except ValueError as exc:
                self.logger.warning(
                    "skipping lever company %r: response was not valid JSON: %s",
                    company.slug,
                    exc,
                )
                continue

            if not isinstance(data, list):
                self.logger.warning(
                    "skipping lever company %r: unexpected response shape", company.slug
                )
                continue

            raw[company.slug] = data

        if not raw and self.companies:
            raise ScraperError("all configured lever companies failed to fetch")

        return raw

    def parse(self, raw: dict[str, list[Any]]) -> list[NormalizedJob]:
        company_by_slug = {c.slug: c.company for c in self.companies}
        jobs: list[NormalizedJob] = []
        for slug, postings in raw.items():
            company_name = company_by_slug.get(slug, slug)
            for item in postings:
                try:
                    jobs.append(self._parse_one(item, company_name))
                except (KeyError, ValueError) as exc:
                    self.logger.warning(
                        "skipping unparsable lever posting id=%r for %r: %s",
                        item.get("id") if isinstance(item, dict) else None,
                        slug,
                        exc,
                    )
        return jobs

    def _parse_one(self, item: dict[str, Any], company_name: str) -> NormalizedJob:
        categories = item.get("categories") or {}
        location = categories.get("location") or None
        workplace_type = item.get("workplaceType")
        if workplace_type:
            location = f"{location} ({workplace_type})" if location else f"({workplace_type})"

        description_parts = [item["description"]]
        for section in item.get("lists") or []:
            heading = section.get("text", "")
            content = section.get("content", "")
            description_parts.append(f"<h3>{heading}</h3>{content}")
        description = "".join(description_parts)

        posted_at = None
        if item.get("createdAt"):
            posted_at = datetime.fromtimestamp(item["createdAt"] / 1000, tz=UTC)

        return NormalizedJob(
            source_board=self.source_board,
            external_id=str(item["id"]),
            title=item["text"],
            company=company_name,
            location=location,
            description=description,
            apply_url=item["applyUrl"],
            posted_at=posted_at,
        )
