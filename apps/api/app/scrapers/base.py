"""Abstract contract every job board scraper implements (Commits 12-14).

This commit defines the interface, shared HTTP/rate-limit utilities, and
the normalized output contract only. No concrete scraper, no dedup hash
computation (Commit 15), no DB writes, no ARQ integration (Commit 17).

## Error contract (decided here, binding on every scraper)

**Total failure** — the source is unreachable, or the top-level response
can't be made sense of at all (not the expected shape; zero listings
identifiable) — raises `ScraperError`. It propagates out of `run()`
uncaught: there is nothing useful to return, and silently returning an
empty list would be indistinguishable from "the board genuinely has zero
open listings today," which is a real and different condition a caller
needs to be able to tell apart from "the scrape failed."

**Partial failure** — most listings parse fine, a handful don't (bad HTML
fragment, missing expected field, etc.) — is *not* raised. `parse()` is
expected to catch each listing's own exception internally, log it via
`self.logger`, skip that one listing, and keep going. `run()` returns
whatever the good listings normalized to; a shorter-than-expected list is
the only signal a caller gets, by design — 3 bad listings out of 50 must
never take down the other 47.

Why raise for one and swallow-and-log for the other: total failure means
the caller has *nothing* — that has to be loud. Partial failure means the
caller has a mostly-good result — failing the whole batch over a handful
of bad listings would make every scraper brittle against the inevitable
one-off malformed listing a real board serves up sooner or later.

## Multi-target sources (Commit 12 extension)

The contract above assumes one source == one HTTP fetch. Commit 12's ATS
scrapers (Greenhouse/Lever/Workable) each fetch N independently-configured
companies per source, which this module didn't originally anticipate.
Extension, not deviation: a single company's fetch failing (bad/stale
slug, unreachable after retries) is treated at the same granularity as a
single bad listing above — logged and skipped, not raised. `ScraperError`
is raised only when *every* configured company for that source fails,
matching the "nothing useful to return" criterion already defined above.
See docs/superpowers/specs/2026-07-02-ats-scrapers-design.md for the full
reasoning.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx

from app.scrapers.http import RateLimiter, ScraperHTTPClient
from app.scrapers.schemas import BoardSource, NormalizedJob


class ScraperError(Exception):
    """Total failure: source unreachable, or its response couldn't be
    interpreted at all. See the module docstring for the full contract."""


class PermanentlyExcludedSourceError(ScraperError):
    """A source this project deliberately does not access, by design
    decision rather than transient failure -- e.g. no compliant API access
    exists and scraping would carry ToS/legal exposure.

    Distinct from a bare ScraperError so an orchestrator (Commit 17) can
    tell "known, permanent, by-design exclusion" apart from "this source is
    broken right now" -- e.g. skip silently on a schedule instead of paging
    on-call -- via isinstance, without hardcoding source names or
    string-matching error messages. `retriable` is always False: by
    definition, retrying does not help an intentional exclusion.
    """

    retriable: ClassVar[bool] = False


class BaseScraper(ABC):
    """Subclasses set `source_board` and implement `fetch()`/`parse()`.
    `run()` is concrete — do not override it.
    """

    source_board: ClassVar[BoardSource]

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limit_seconds: float | None = None,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """All timing/retry/rate-limit knobs are config, not constants —
        each scraper (Commits 12-14) passes its own source-appropriate
        values here; nothing in this shared layer hardcodes them.

        `transport` is None in real use (httpx's normal live-network
        transport) and only ever set to `httpx.MockTransport(...)` in
        tests, so a scraper's fetch loop can be tested deterministically
        without hitting the network — see Commit 12's multi-company
        fetch-loop tests for the pattern."""

        rate_limiter = RateLimiter(rate_limit_seconds) if rate_limit_seconds else None
        self.http = ScraperHTTPClient(
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_base_seconds=backoff_base_seconds,
            rate_limiter=rate_limiter,
            headers=headers,
            transport=transport,
        )
        self.logger = logging.getLogger(f"{__name__}.{type(self).__name__}")

    @abstractmethod
    async def fetch(self) -> Any:
        """Fetch raw response(s) from the source, via `self.http`.

        Raises `ScraperError` on total failure. `ScraperHTTPClient` already
        retries transient failures (429/5xx/network errors) with backoff;
        by the time an exception reaches here, retries are exhausted —
        wrap it in `ScraperError` (or let a non-retryable 4xx propagate
        as one) rather than leaking `httpx` exceptions to callers.
        """

    @abstractmethod
    def parse(self, raw: Any) -> list[NormalizedJob]:
        """Parse a raw response into normalized jobs.

        Must not raise for a single bad listing — catch it, log via
        `self.logger.warning(...)`, skip it, continue with the rest. Only
        raise `ScraperError` if the *entire* response is unusable (e.g.
        the expected top-level structure isn't there at all).
        """

    async def run(self) -> list[NormalizedJob]:
        """Orchestrates fetch -> parse -> normalized jobs. Not persistence,
        not dedup — see the module docstring for what `parse()` owns vs
        what later commits own."""

        async with self.http:
            raw = await self.fetch()
        return self.parse(raw)
