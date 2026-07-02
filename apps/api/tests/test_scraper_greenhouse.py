"""Tests for GreenhouseScraper (Commit 12).

All HTTP in this file is mocked via `httpx.MockTransport` with fixture JSON
responses shaped like Greenhouse's real API (confirmed live against
boards-api.greenhouse.io before writing app/scrapers/greenhouse.py -- see
docs/superpowers/specs/2026-07-02-ats-scrapers-design.md). No test in this
file makes a real network call; `_RecordingTransport` below records every
request it's asked to resolve so that claim is asserted on directly, not
just implied by "tests passed".
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from app.scrapers.base import ScraperError
from app.scrapers.config.loader import CompanyConfig
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.schemas import NormalizedJob


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Wraps a handler fn and records every request it resolves. Used to
    prove -- not just assume -- that a test never reaches the real
    network: `calls` is asserted on directly in every fetch-loop test."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.calls: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self._handler(request)


_STRIPE_LISTING_1: dict[str, Any] = {
    "id": 7954688,
    "title": "Account Executive, AI Sales (Grower)",
    "location": {"name": "San Francisco, CA"},
    "content": "<p>About the role...</p>",
    "absolute_url": "https://stripe.com/jobs/search?gh_jid=7954688",
    "first_published": "2026-06-02T08:58:57-04:00",
}

_STRIPE_LISTING_2: dict[str, Any] = {
    "id": 1111111,
    "title": "Software Engineer, Infra",
    "location": {"name": "Remote"},
    "content": "<p>Infra role...</p>",
    "absolute_url": "https://stripe.com/jobs/search?gh_jid=1111111",
    "first_published": "2026-05-01T00:00:00-04:00",
}

_GITLAB_LISTING: dict[str, Any] = {
    "id": 2222222,
    "title": "Site Reliability Engineer",
    "location": {"name": "Dublin, Ireland"},
    "content": "<p>SRE role...</p>",
    "absolute_url": "https://gitlab.com/jobs/2222222",
    "first_published": "2026-04-15T00:00:00-04:00",
}

_STRIPE = CompanyConfig(slug="stripe", company="Stripe")
_GITLAB = CompanyConfig(slug="gitlab", company="GitLab")


# --- parse(): field mapping ---------------------------------------------------


def test_greenhouse_parse_maps_all_fields() -> None:
    scraper = GreenhouseScraper(companies=[_STRIPE])

    jobs = scraper.parse({"stripe": [_STRIPE_LISTING_1]})

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_board == "greenhouse"
    assert job.external_id == "7954688"
    assert job.title == "Account Executive, AI Sales (Grower)"
    assert job.company == "Stripe"
    assert job.location == "San Francisco, CA"
    assert job.description == "<p>About the role...</p>"
    assert job.apply_url == "https://stripe.com/jobs/search?gh_jid=7954688"
    assert job.posted_at is not None
    assert job.posted_at.year == 2026
    assert job.stack_tags == []


def test_greenhouse_parse_skips_bad_listing_without_raising() -> None:
    scraper = GreenhouseScraper(companies=[_STRIPE])
    bad_listing = {**_STRIPE_LISTING_1, "id": 999}
    del bad_listing["title"]  # missing required field -> KeyError

    jobs = scraper.parse({"stripe": [_STRIPE_LISTING_1, bad_listing]})

    assert len(jobs) == 1
    assert jobs[0].external_id == "7954688"


def test_greenhouse_rate_limit_defaults_to_0_75_seconds() -> None:
    scraper = GreenhouseScraper(companies=[_STRIPE])

    assert scraper.http._rate_limiter is not None
    assert scraper.http._rate_limiter._min_interval == 0.75


# --- fetch()+run(): happy path, multiple companies, multiple jobs ------------


async def test_greenhouse_happy_path_multiple_companies_multiple_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/stripe/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_STRIPE_LISTING_1, _STRIPE_LISTING_2]})
        if "/boards/gitlab/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_GITLAB_LISTING]})
        raise AssertionError(f"unexpected request to {request.url}")

    transport = _RecordingTransport(handler)
    scraper = GreenhouseScraper(
        companies=[_STRIPE, _GITLAB], transport=transport, rate_limit_seconds=0
    )

    jobs = await scraper.run()

    assert len(jobs) == 3
    assert {job.external_id for job in jobs} == {"7954688", "1111111", "2222222"}
    assert {job.company for job in jobs} == {"Stripe", "GitLab"}
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "greenhouse" for job in jobs)

    # Proof of no live network calls: exactly one request per configured
    # company, both resolved entirely by the mock transport.
    assert len(transport.calls) == 2
    assert {str(c.url).split("?")[0] for c in transport.calls} == {
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs",
        "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs",
    }


# --- fetch(): partial failure (one company down, others still succeed) ------


async def test_greenhouse_fetch_skips_company_that_404s_and_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/stripe/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_STRIPE_LISTING_1]})
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [_STRIPE, CompanyConfig(slug="not-a-real-board-xyz", company="Nobody")]
    scraper = GreenhouseScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with caplog.at_level(logging.WARNING):
        async with scraper.http:
            raw = await scraper.fetch()

    assert list(raw.keys()) == ["stripe"]
    assert len(transport.calls) == 2  # both companies attempted, no live calls
    assert any("not-a-real-board-xyz" in record.message for record in caplog.records)


async def test_greenhouse_fetch_raises_scraper_error_when_all_companies_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [
        CompanyConfig(slug="not-a-real-board-1", company="Nobody One"),
        CompanyConfig(slug="not-a-real-board-2", company="Nobody Two"),
    ]
    scraper = GreenhouseScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()

    assert len(transport.calls) == 2  # both attempted before raising, no live calls


# --- fetch(): malformed / unexpected response shape --------------------------


async def test_greenhouse_fetch_skips_company_with_unexpected_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/stripe/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_STRIPE_LISTING_1]})
        # gitlab responds 200 but with a shape that isn't {"jobs": [...]}
        # at all -- e.g. an upstream error payload -- must not crash.
        return httpx.Response(200, json={"error": "unexpected"})

    transport = _RecordingTransport(handler)
    scraper = GreenhouseScraper(
        companies=[_STRIPE, _GITLAB],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["stripe"]
    assert len(transport.calls) == 2


async def test_greenhouse_fetch_skips_company_with_invalid_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/stripe/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_STRIPE_LISTING_1]})
        return httpx.Response(200, content=b"not json at all {{{")

    transport = _RecordingTransport(handler)
    scraper = GreenhouseScraper(
        companies=[_STRIPE, _GITLAB],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["stripe"]
    assert len(transport.calls) == 2


# --- fetch(): empty job list for a company is valid, not an error -----------


async def test_greenhouse_fetch_treats_empty_job_list_as_valid_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/boards/stripe/" in str(request.url):
            return httpx.Response(200, json={"jobs": [_STRIPE_LISTING_1]})
        return httpx.Response(200, json={"jobs": []})  # gitlab has zero openings today

    transport = _RecordingTransport(handler)
    scraper = GreenhouseScraper(
        companies=[_STRIPE, _GITLAB],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert raw == {"stripe": [_STRIPE_LISTING_1], "gitlab": []}
    jobs = scraper.parse(raw)
    assert len(jobs) == 1
    assert len(transport.calls) == 2
