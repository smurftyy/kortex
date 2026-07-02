"""RemoteOK scraper.

RemoteOK exposes a genuine, open, no-auth JSON API at
https://remoteok.com/api — confirmed live before writing this file. No HTML
parsing required.

## robots.txt

`User-agent: *` sets `Allow: /` and `Crawl-delay: 1`. Separately,
`User-agent: ClaudeBot` (and GPTBot/CCBot/Google-Extended/etc.) is
`Disallow: /`, and `Content-Signal: ai-train=no` applies generally. That
disallow targets Anthropic's own crawler specifically; this scraper is
Kortex's own service, identifying as `KortexBot/1.0`, not `ClaudeBot` — a
distinct piece of software the same way anything written with AI coding
assistance isn't bound by the vendor's own separate crawler rules. It does
not use RemoteOK's content to train anything; it aggregates listings for
Kortex's own users. `Crawl-delay: 1` is honored as the rate limit below.

## Response shape

`GET /api` returns a JSON array. Index 0 is always a legal/metadata notice
(`{"legal": "...", "last_updated": ...}`), not a listing — it has none of a
real listing's fields and is skipped via the same per-item partial-failure
path as any other malformed entry, not special-cased.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.schemas import NormalizedJob

_API_URL = "https://remoteok.com/api"
_USER_AGENT = "KortexBot/1.0 (+https://kortex.example; job board aggregator)"


class RemoteOKScraper(BaseScraper):
    source_board = "remoteok"

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limit_seconds: float = 1.0,  # robots.txt: Crawl-delay: 1
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_base_seconds=backoff_base_seconds,
            rate_limit_seconds=rate_limit_seconds,
            headers={"User-Agent": _USER_AGENT},
        )

    async def fetch(self) -> list[Any]:
        try:
            response = await self.http.get(_API_URL)
        except httpx.HTTPError as exc:
            raise ScraperError(f"RemoteOK unreachable: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ScraperError(f"RemoteOK response was not valid JSON: {exc}") from exc

        if not isinstance(data, list) or not data:
            raise ScraperError("RemoteOK response was not the expected JSON array")

        return data

    def parse(self, raw: list[Any]) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        for item in raw:
            if not isinstance(item, dict) or "id" not in item:
                # The feed's own leading legal/metadata notice lands here —
                # no special-casing, it's just another item without the
                # fields a real listing has.
                continue

            try:
                jobs.append(self._parse_one(item))
            except (KeyError, ValueError) as exc:
                self.logger.warning(
                    "skipping unparsable RemoteOK listing id=%r: %s", item.get("id"), exc
                )

        return jobs

    def _parse_one(self, item: dict[str, Any]) -> NormalizedJob:
        posted_at = None
        if item.get("date"):
            posted_at = datetime.fromisoformat(item["date"])

        location = item.get("location") or None
        if location:
            location = location.strip().strip(",").strip() or None

        return NormalizedJob(
            source_board=self.source_board,
            external_id=str(item["id"]),
            title=item["position"],
            company=item["company"],
            location=location,
            description=item["description"],
            stack_tags=[str(tag) for tag in item.get("tags", [])],
            apply_url=item["apply_url"],
            posted_at=posted_at,
        )
