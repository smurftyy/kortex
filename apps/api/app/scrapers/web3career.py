"""Web3.career scraper.

Web3.career exposes a documented, tokened JSON API --
`GET https://web3.career/api/v1?token=...` -- confirmed via its published
OpenAPI spec (docs.bondex.app/api-reference), not HTML scraping. See
docs/superpowers/specs/2026-07-03-web3career-scraper-design.md for the full
investigation: why this isn't HTML parsing, why no `CompanyConfig` entry is
used, and an honest brittleness assessment (no API token was available to
validate live, so unlike RemoteOK/Greenhouse/Lever/Workable there is no
live end-to-end test for this scraper -- mocked-only, against the spec's
documented schema).

## Response shape

The spec's own words: the top-level response is `[string, string, Job[]]`
in the common case -- "extract jobs by finding the first element that is
itself an array" -- but documents a fallback where "the root array may
directly contain job objects." Both are handled in `fetch()`.

## Single aggregator, not per-company

Unlike Greenhouse/Lever/Workable, this is one account/token returning
listings across many companies in one call -- there is no per-company slug
to configure, so this scraper does not use `app/scrapers/config/loader.py`
at all (same reasoning as `RemoteOKScraper`). `company` is taken directly
from each listing in the response, since there's no config value to prefer
instead and the API does supply a real per-listing company name.

## Fields Commit 11's schema can't represent

`remote: true` is folded into `location` as a `"(Remote)"` suffix, same
approach as `LeverScraper`'s `workplaceType`/`WorkableScraper`'s
`telecommuting` -- except here the source's own example data shows
`location` sometimes already reading `"Remote"` for a remote listing, so
the suffix is only appended when `location` doesn't already say so
(case-insensitively), to avoid a nonsensical "Remote (Remote)". `salary`
and `url` (the non-tracking page link) are discarded -- no `NormalizedJob`
field fits either, and `apply_url` is the field the API's own terms of use
requires using for outbound links, not `url`.

`postedAt`'s format is explicitly undocumented ("format may vary between
listings," per the spec) -- parsed defensively via `datetime.fromisoformat`
with a fallback to `None` on failure, since `NormalizedJob.posted_at` is
optional: a bad date degrades one field, not the whole listing.

## No pagination

The API has no offset/cursor/page parameter -- "results are always the
most recent listings." This scraper requests the maximum `limit=100` and
does not attempt to page or fan out across the `tag` enum for broader
coverage (see the design doc's "explicitly out of scope").
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.schemas import NormalizedJob

_API_URL = "https://web3.career/api/v1"
_USER_AGENT = "KortexBot/1.0 (+https://kortex.example; job board aggregator)"


class Web3CareerScraper(BaseScraper):
    source_board = "web3career"

    def __init__(
        self,
        *,
        api_token: str,
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
        self._api_token = api_token

    async def fetch(self) -> list[Any]:
        try:
            response = await self.http.get(
                _API_URL,
                params={"token": self._api_token, "limit": 100, "show_description": "true"},
            )
        except httpx.HTTPError as exc:
            raise ScraperError(f"Web3.career unreachable: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperError(f"Web3.career response was not valid JSON: {exc}") from exc

        jobs = self._extract_jobs(data)
        if jobs is None:
            raise ScraperError("Web3.career response was not the expected shape")

        return jobs

    @staticmethod
    def _extract_jobs(data: Any) -> list[Any] | None:
        """Per the OpenAPI spec: the top-level array is typically
        `[string, string, Job[]]` -- find the first element that is itself
        a list. Documented fallback: the root array may directly contain
        job objects instead."""

        if not isinstance(data, list):
            return None

        for element in data:
            if isinstance(element, list):
                return element

        if all(isinstance(element, dict) for element in data):
            return data

        return None

    def parse(self, raw: list[Any]) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            try:
                jobs.append(self._parse_one(item))
            except (KeyError, ValueError) as exc:
                self.logger.warning(
                    "skipping unparsable web3career listing id=%r: %s", item.get("id"), exc
                )

        return jobs

    def _parse_one(self, item: dict[str, Any]) -> NormalizedJob:
        location = item.get("location") or None
        if item.get("remote") and (not location or "remote" not in location.lower()):
            location = f"{location} (Remote)" if location else "(Remote)"

        posted_at = None
        raw_posted_at = item.get("postedAt")
        if raw_posted_at:
            try:
                posted_at = datetime.fromisoformat(raw_posted_at)
            except ValueError:
                self.logger.debug("unparseable web3career postedAt=%r", raw_posted_at)

        return NormalizedJob(
            source_board=self.source_board,
            external_id=str(item["id"]),
            title=item["title"],
            company=item["company"],
            location=location,
            description=item["description"],
            stack_tags=[str(tag) for tag in item.get("tags", [])],
            apply_url=item["apply_url"],
            posted_at=posted_at,
        )
