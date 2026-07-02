"""Tests for WorkableScraper (Commit 12).

All HTTP in this file is mocked via `httpx.MockTransport` with fixture JSON
responses shaped like Workable's real API (confirmed live against
apply.workable.com, with `details=true`, before writing
app/scrapers/workable.py -- see docs/superpowers/specs/
2026-07-02-ats-scrapers-design.md). No test in this file makes a real
network call; `_RecordingTransport` below records every request it's asked
to resolve so that claim is asserted on directly, not just implied by
"tests passed". Same structure/categories as test_scraper_greenhouse.py and
test_scraper_lever.py, adapted to Workable's `{"name", "jobs": [...]}`
envelope (unlike Lever's bare array) and its `city`/`state`/`country` +
`telecommuting` location fields (unlike Greenhouse's single `location.name`
or Lever's `categories.location` + `workplaceType`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from app.scrapers.base import ScraperError
from app.scrapers.config.loader import CompanyConfig
from app.scrapers.schemas import NormalizedJob
from app.scrapers.workable import WorkableScraper


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


_ZEGO_JOB_1: dict[str, Any] = {
    "title": "Claims Handler - Third Party",
    "shortcode": "450EC5C378",
    "city": "Halifax",
    "state": "England",
    "country": "United Kingdom",
    "telecommuting": False,
    "application_url": "https://apply.workable.com/j/450EC5C378/apply",
    "published_on": "2025-09-04",
    "description": "<p>About Zego...</p>",
}

_ZEGO_JOB_2: dict[str, Any] = {
    "title": "Senior Data Scientist",
    "shortcode": "9AA0B1C2D3",
    "city": "",
    "state": "",
    "country": "",
    "telecommuting": True,
    "application_url": "https://apply.workable.com/j/9AA0B1C2D3/apply",
    "published_on": "2025-10-11",
    "description": "<p>Data role...</p>",
}

_ACME_JOB: dict[str, Any] = {
    "title": "Account Manager",
    "shortcode": "ACME12345",
    "city": "Austin",
    "state": "TX",
    "country": "United States",
    "telecommuting": False,
    "application_url": "https://apply.workable.com/j/ACME12345/apply",
    "published_on": "2025-08-01",
    "description": "<p>Sales role...</p>",
}

_ZEGO = CompanyConfig(slug="zego", company="Zego")
_ACME = CompanyConfig(slug="acme", company="Acme")


# --- parse(): field mapping ---------------------------------------------------


def test_workable_parse_maps_all_fields() -> None:
    scraper = WorkableScraper(companies=[_ZEGO])

    jobs = scraper.parse({"zego": [_ZEGO_JOB_1]})

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_board == "workable"
    assert job.external_id == "450EC5C378"
    assert job.title == "Claims Handler - Third Party"
    assert job.company == "Zego"
    assert job.location == "Halifax, England, United Kingdom"
    assert job.description == "<p>About Zego...</p>"
    assert job.apply_url == "https://apply.workable.com/j/450EC5C378/apply"
    assert job.posted_at is not None
    assert job.posted_at.year == 2025
    assert job.stack_tags == []


def test_workable_location_gets_remote_suffix_when_telecommuting() -> None:
    scraper = WorkableScraper(companies=[_ZEGO])
    job = {**_ZEGO_JOB_1, "telecommuting": True}

    jobs = scraper.parse({"zego": [job]})

    assert jobs[0].location == "Halifax, England, United Kingdom (Remote)"


def test_workable_location_is_just_remote_suffix_when_no_city_state_country() -> None:
    scraper = WorkableScraper(companies=[_ZEGO])

    jobs = scraper.parse({"zego": [_ZEGO_JOB_2]})

    assert jobs[0].location == "(Remote)"


def test_workable_parse_skips_bad_listing_without_raising() -> None:
    scraper = WorkableScraper(companies=[_ZEGO])
    bad_job = {**_ZEGO_JOB_1, "shortcode": "BAD1"}
    del bad_job["title"]  # missing required field -> KeyError

    jobs = scraper.parse({"zego": [_ZEGO_JOB_1, bad_job]})

    assert len(jobs) == 1
    assert jobs[0].external_id == "450EC5C378"


def test_workable_rate_limit_defaults_to_0_5_seconds() -> None:
    scraper = WorkableScraper(companies=[_ZEGO])

    assert scraper.http._rate_limiter is not None
    assert scraper.http._rate_limiter._min_interval == 0.5


# --- fetch()+run(): happy path, multiple companies, multiple jobs ------------


async def test_workable_happy_path_multiple_companies_multiple_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/accounts/zego" in str(request.url):
            return httpx.Response(200, json={"name": "Zego", "jobs": [_ZEGO_JOB_1, _ZEGO_JOB_2]})
        if "/accounts/acme" in str(request.url):
            return httpx.Response(200, json={"name": "Acme", "jobs": [_ACME_JOB]})
        raise AssertionError(f"unexpected request to {request.url}")

    transport = _RecordingTransport(handler)
    scraper = WorkableScraper(companies=[_ZEGO, _ACME], transport=transport, rate_limit_seconds=0)

    jobs = await scraper.run()

    assert len(jobs) == 3
    assert {job.external_id for job in jobs} == {"450EC5C378", "9AA0B1C2D3", "ACME12345"}
    assert {job.company for job in jobs} == {"Zego", "Acme"}
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "workable" for job in jobs)

    # Proof of no live network calls: exactly one request per configured
    # company, both resolved entirely by the mock transport.
    assert len(transport.calls) == 2
    assert {str(c.url).split("?")[0] for c in transport.calls} == {
        "https://apply.workable.com/api/v1/widget/accounts/zego",
        "https://apply.workable.com/api/v1/widget/accounts/acme",
    }
    assert all(c.url.params.get("details") == "true" for c in transport.calls)


# --- fetch(): partial failure (one company down, others still succeed) ------


async def test_workable_fetch_skips_company_that_404s_and_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/accounts/zego" in str(request.url):
            return httpx.Response(200, json={"name": "Zego", "jobs": [_ZEGO_JOB_1]})
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [_ZEGO, CompanyConfig(slug="not-a-real-account-xyz", company="Nobody")]
    scraper = WorkableScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with caplog.at_level(logging.WARNING):
        async with scraper.http:
            raw = await scraper.fetch()

    assert list(raw.keys()) == ["zego"]
    assert len(transport.calls) == 2  # both companies attempted, no live calls
    assert any("not-a-real-account-xyz" in record.message for record in caplog.records)


async def test_workable_fetch_raises_scraper_error_when_all_companies_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [
        CompanyConfig(slug="not-a-real-account-1", company="Nobody One"),
        CompanyConfig(slug="not-a-real-account-2", company="Nobody Two"),
    ]
    scraper = WorkableScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()

    assert len(transport.calls) == 2  # both attempted before raising, no live calls


async def test_workable_fetch_raises_scraper_error_when_the_single_configured_company_fails() -> (
    None
):
    """`boards.json` configures exactly one Workable company ("zego")
    today -- the "all configured companies fail" path must still be
    exercised (and still raise) when N == 1."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    scraper = WorkableScraper(
        companies=[_ZEGO],
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()

    assert len(transport.calls) == 1  # the one configured company was attempted, no live calls


# --- fetch(): malformed / unexpected response shape --------------------------


async def test_workable_fetch_skips_company_with_unexpected_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/accounts/zego" in str(request.url):
            return httpx.Response(200, json={"name": "Zego", "jobs": [_ZEGO_JOB_1]})
        # acme responds 200 but with a shape that isn't {"jobs": [...]}
        # at all -- e.g. an upstream error payload -- must not crash.
        return httpx.Response(200, json={"error": "unexpected"})

    transport = _RecordingTransport(handler)
    scraper = WorkableScraper(
        companies=[_ZEGO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["zego"]
    assert len(transport.calls) == 2


async def test_workable_fetch_skips_company_with_invalid_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/accounts/zego" in str(request.url):
            return httpx.Response(200, json={"name": "Zego", "jobs": [_ZEGO_JOB_1]})
        return httpx.Response(200, content=b"not json at all {{{")

    transport = _RecordingTransport(handler)
    scraper = WorkableScraper(
        companies=[_ZEGO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["zego"]
    assert len(transport.calls) == 2


# --- fetch(): empty job list for a company is valid, not an error -----------


async def test_workable_fetch_treats_empty_job_list_as_valid_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/accounts/zego" in str(request.url):
            return httpx.Response(200, json={"name": "Zego", "jobs": [_ZEGO_JOB_1]})
        return httpx.Response(200, json={"name": "Acme", "jobs": []})  # zero openings today

    transport = _RecordingTransport(handler)
    scraper = WorkableScraper(
        companies=[_ZEGO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert raw == {"zego": [_ZEGO_JOB_1], "acme": []}
    jobs = scraper.parse(raw)
    assert len(jobs) == 1
    assert len(transport.calls) == 2
