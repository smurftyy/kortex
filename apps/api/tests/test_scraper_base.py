"""Tests for the Commit 11 scraper base contract.

`_DemoScraper` below is test-only scaffolding to exercise `BaseScraper`
end-to-end — it is not a board scraper and never ships. Per the validation
standard for this commit, the primary success-path test hits a real,
public, stable, low-traffic-concern endpoint
(https://jsonplaceholder.typicode.com — a long-standing, purpose-built
"fake JSON API for testing" service, no auth, no meaningful rate limit for
a handful of requests) rather than mocking the network. Retry/backoff edge
cases use `httpx.MockTransport` instead, since those need to be fast and
deterministic (simulating specific failure sequences), not because the
live endpoint is being avoided for the core contract.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest
from app.scrapers.base import BaseScraper, PermanentlyExcludedSourceError, ScraperError
from app.scrapers.http import RateLimiter, ScraperHTTPClient
from app.scrapers.schemas import NormalizedJob
from pydantic import ValidationError

JSONPLACEHOLDER_POSTS_URL = "https://jsonplaceholder.typicode.com/posts"


class _DemoScraper(BaseScraper):
    """Test-only: maps jsonplaceholder posts onto NormalizedJob to prove
    fetch -> parse -> normalize works against a real HTTP target."""

    source_board = "greenhouse"  # stand-in value; jsonplaceholder isn't a real board

    async def fetch(self) -> list[dict[str, Any]]:
        try:
            response = await self.http.get(JSONPLACEHOLDER_POSTS_URL, params={"_limit": 5})
        except httpx.HTTPError as exc:
            raise ScraperError(f"could not fetch from jsonplaceholder: {exc}") from exc
        data = response.json()
        if not isinstance(data, list):
            raise ScraperError("expected a JSON array of posts")
        return data

    def parse(self, raw: list[dict[str, Any]]) -> list[NormalizedJob]:
        jobs: list[NormalizedJob] = []
        for item in raw:
            try:
                jobs.append(
                    NormalizedJob(
                        source_board=self.source_board,
                        external_id=str(item["id"]),
                        title=item["title"],
                        company=f"Demo Co {item['userId']}",
                        description=item["body"],
                        apply_url=f"{JSONPLACEHOLDER_POSTS_URL}/{item['id']}",
                    )
                )
            except (KeyError, ValidationError) as exc:
                self.logger.warning("skipping unparsable listing %r: %s", item, exc)
        return jobs


# --- live end-to-end validation ---------------------------------------------


async def test_live_fetch_parse_normalize_end_to_end() -> None:
    scraper = _DemoScraper(backoff_base_seconds=0.05)

    jobs = await scraper.run()

    assert len(jobs) == 5
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "greenhouse" for job in jobs)
    assert all(job.apply_url.startswith(JSONPLACEHOLDER_POSTS_URL + "/") for job in jobs)
    assert all(job.title for job in jobs)
    assert all(job.description for job in jobs)


# --- error contract ----------------------------------------------------------


async def test_run_raises_scraper_error_on_total_failure() -> None:
    """Unreachable source -> ScraperError, not a raw httpx/network exception."""

    class _UnreachableScraper(BaseScraper):
        source_board = "greenhouse"

        async def fetch(self) -> Any:
            try:
                await self.http.get("http://127.0.0.1:1/definitely-not-listening")
            except httpx.HTTPError as exc:
                raise ScraperError(f"unreachable: {exc}") from exc

        def parse(self, raw: Any) -> list[NormalizedJob]:
            raise AssertionError("parse() should never run when fetch() fails")

    scraper = _UnreachableScraper(max_retries=1, backoff_base_seconds=0.01)

    with pytest.raises(ScraperError):
        await scraper.run()


def test_parse_skips_bad_listings_without_raising() -> None:
    """3 bad listings out of 5 -> parse() returns the 2 good ones, doesn't raise."""

    scraper = _DemoScraper()
    raw = [
        {"id": 1, "userId": 1, "title": "Good listing one", "body": "desc"},
        {"id": 2, "userId": 1, "body": "missing title -> KeyError"},
        {"id": 3, "userId": 1, "title": "", "body": "desc"},  # empty title still valid str
        {"id": 4, "userId": 1, "title": "Good listing two", "body": "desc"},
        {"userId": 1, "title": "missing id -> KeyError", "body": "desc"},
    ]

    jobs = scraper.parse(raw)

    assert len(jobs) == 3  # ids 1, 3 (empty title is valid), 4 -- ids 2 and the last are dropped
    assert {job.title for job in jobs} == {"Good listing one", "", "Good listing two"}


# --- rate limiter --------------------------------------------------------------


async def test_rate_limiter_enforces_minimum_interval() -> None:
    limiter = RateLimiter(min_interval_seconds=0.2)

    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - start

    # 3 acquisitions, 2 gaps of >= 0.2s each.
    assert elapsed >= 0.4


async def test_rate_limiter_does_not_delay_first_call() -> None:
    limiter = RateLimiter(min_interval_seconds=5.0)

    start = time.monotonic()
    await limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed < 0.1


# --- injectable transport (Commit 12 needs this for multi-company fetch tests) ---


async def test_base_scraper_accepts_injectable_transport_for_testing() -> None:
    """Commit 12's ATS scrapers unit-test their per-company fetch loop
    deterministically via httpx.MockTransport, injected through a scraper
    subclass rather than by constructing ScraperHTTPClient directly (which
    the existing retry-path tests above already do). BaseScraper needs to
    accept and forward `transport` for that to work."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    class _TransportDemoScraper(BaseScraper):
        source_board = "greenhouse"

        async def fetch(self) -> Any:
            response = await self.http.get("https://example.invalid/x")
            return response.json()

        def parse(self, raw: Any) -> list[NormalizedJob]:
            return []

    scraper = _TransportDemoScraper(transport=transport)
    result = await scraper.run()

    assert result == []


# --- retry-with-backoff (deterministic, via MockTransport) ---------------------


async def test_http_client_retries_transient_failures_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with ScraperHTTPClient(
        max_retries=3, backoff_base_seconds=0.01, transport=transport
    ) as client:
        response = await client.get("https://example.invalid/x")

    assert response.status_code == 200
    assert attempts == 3


async def test_http_client_does_not_retry_non_retryable_4xx() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with ScraperHTTPClient(
        max_retries=3, backoff_base_seconds=0.01, transport=transport
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.invalid/x")

    assert attempts == 1  # no retries burned on a non-retryable status


async def test_http_client_raises_after_exhausting_retries() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    async with ScraperHTTPClient(
        max_retries=2, backoff_base_seconds=0.01, transport=transport
    ) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get("https://example.invalid/x")

    assert attempts == 3  # initial attempt + 2 retries


# --- schema validation -----------------------------------------------------------


def test_normalized_job_rejects_unknown_source_board() -> None:
    with pytest.raises(ValidationError):
        NormalizedJob(
            source_board="not-a-real-board",  # type: ignore[arg-type]
            title="x",
            company="x",
            description="x",
            apply_url="https://example.com/job/1",
        )


def test_normalized_job_rejects_non_url_apply_url() -> None:
    with pytest.raises(ValidationError):
        NormalizedJob(
            source_board="greenhouse",
            title="x",
            company="x",
            description="x",
            apply_url="not-a-url",
        )


def test_normalized_job_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        NormalizedJob(
            source_board="greenhouse",
            title="x",
            company="x",
            description="x",
            apply_url="https://example.com/job/1",
            dedup_hash="should-not-be-settable-here",  # type: ignore[call-arg]
        )


# --- permanently-excluded sources ---------------------------------------------


def test_permanently_excluded_source_error_is_a_scraper_error() -> None:
    error = PermanentlyExcludedSourceError("excluded by design")

    assert isinstance(error, ScraperError)


def test_permanently_excluded_source_error_is_never_retriable() -> None:
    error = PermanentlyExcludedSourceError("excluded by design")

    assert error.retriable is False
