"""Tests for LeverScraper (Commit 12).

All HTTP in this file is mocked via `httpx.MockTransport` with fixture JSON
responses shaped like Lever's real API (confirmed live against api.lever.co
before writing app/scrapers/lever.py -- see docs/superpowers/specs/
2026-07-02-ats-scrapers-design.md). No test in this file makes a real
network call; `_RecordingTransport` below records every request it's asked
to resolve so that claim is asserted on directly, not just implied by
"tests passed". Same structure/categories as test_scraper_greenhouse.py,
adapted to Lever's response shape (a bare JSON array, not `{"jobs": [...]}`,
and no per-company "GitLab"-equivalent second seed company -- `boards.json`
only configures "ro" for Lever today, so the multi-company happy-path and
skip-one-continue tests use a second, made-up company via the `companies=`
override rather than the seed config).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from app.scrapers.base import ScraperError
from app.scrapers.config.loader import CompanyConfig
from app.scrapers.lever import LeverScraper
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


_RO_POSTING_1: dict[str, Any] = {
    "id": "bde27362-0652-4d1a-bb8e-d6100ca20654",
    "text": "Associate Director, Growth",
    "categories": {"location": "New York, NY", "commitment": "Full-time", "team": "Growth"},
    "workplaceType": "hybrid",
    "description": "<p>Intro paragraph.</p>",
    "lists": [
        {"text": "What You'll Do:", "content": "<li>Do things</li>"},
        {"text": "What You'll Bring:", "content": "<li>Skills</li>"},
    ],
    "applyUrl": "https://jobs.lever.co/ro/bde27362-0652-4d1a-bb8e-d6100ca20654/apply",
    "createdAt": 1773176562892,
}

_RO_POSTING_2: dict[str, Any] = {
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "text": "Senior Backend Engineer",
    "categories": {"location": "Remote", "commitment": "Full-time", "team": "Engineering"},
    "workplaceType": "remote",
    "description": "<p>Backend role.</p>",
    "lists": [],
    "applyUrl": "https://jobs.lever.co/ro/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/apply",
    "createdAt": 1770000000000,
}

_ACME_POSTING: dict[str, Any] = {
    "id": "11111111-2222-3333-4444-555555555555",
    "text": "Product Designer",
    "categories": {"location": "Austin, TX", "commitment": "Full-time", "team": "Design"},
    "workplaceType": "onsite",
    "description": "<p>Design role.</p>",
    "lists": [],
    "applyUrl": "https://jobs.lever.co/acme/11111111-2222-3333-4444-555555555555/apply",
    "createdAt": 1768000000000,
}

_RO = CompanyConfig(slug="ro", company="Ro")
_ACME = CompanyConfig(slug="acme", company="Acme")


# --- parse(): field mapping ---------------------------------------------------


def test_lever_parse_maps_all_fields_and_folds_lists_into_description() -> None:
    scraper = LeverScraper(companies=[_RO])

    jobs = scraper.parse({"ro": [_RO_POSTING_1]})

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_board == "lever"
    assert job.external_id == "bde27362-0652-4d1a-bb8e-d6100ca20654"
    assert job.title == "Associate Director, Growth"
    assert job.company == "Ro"
    assert job.location == "New York, NY (hybrid)"
    assert "Intro paragraph." in job.description
    assert "What You'll Do:" in job.description
    assert "Do things" in job.description
    assert "What You'll Bring:" in job.description
    assert job.apply_url == "https://jobs.lever.co/ro/bde27362-0652-4d1a-bb8e-d6100ca20654/apply"
    assert job.posted_at is not None
    assert job.posted_at.year == 2026
    assert job.stack_tags == []


def test_lever_location_is_just_workplace_type_when_location_missing() -> None:
    scraper = LeverScraper(companies=[_RO])
    posting = {**_RO_POSTING_1, "categories": {}}

    jobs = scraper.parse({"ro": [posting]})

    assert jobs[0].location == "(hybrid)"


def test_lever_parse_skips_bad_listing_without_raising() -> None:
    scraper = LeverScraper(companies=[_RO])
    bad_posting = {**_RO_POSTING_1, "id": "bad-1"}
    del bad_posting["text"]  # missing required field -> KeyError

    jobs = scraper.parse({"ro": [_RO_POSTING_1, bad_posting]})

    assert len(jobs) == 1
    assert jobs[0].external_id == "bde27362-0652-4d1a-bb8e-d6100ca20654"


def test_lever_rate_limit_defaults_to_crawl_delay_1_second() -> None:
    scraper = LeverScraper(companies=[_RO])

    assert scraper.http._rate_limiter is not None
    assert scraper.http._rate_limiter._min_interval == 1.0


# --- fetch()+run(): happy path, multiple companies, multiple jobs ------------


async def test_lever_happy_path_multiple_companies_multiple_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/postings/ro" in str(request.url):
            return httpx.Response(200, json=[_RO_POSTING_1, _RO_POSTING_2])
        if "/postings/acme" in str(request.url):
            return httpx.Response(200, json=[_ACME_POSTING])
        raise AssertionError(f"unexpected request to {request.url}")

    transport = _RecordingTransport(handler)
    scraper = LeverScraper(companies=[_RO, _ACME], transport=transport, rate_limit_seconds=0)

    jobs = await scraper.run()

    assert len(jobs) == 3
    assert {job.external_id for job in jobs} == {
        "bde27362-0652-4d1a-bb8e-d6100ca20654",
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "11111111-2222-3333-4444-555555555555",
    }
    assert {job.company for job in jobs} == {"Ro", "Acme"}
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "lever" for job in jobs)

    # Proof of no live network calls: exactly one request per configured
    # company, both resolved entirely by the mock transport.
    assert len(transport.calls) == 2
    assert {str(c.url).split("?")[0] for c in transport.calls} == {
        "https://api.lever.co/v0/postings/ro",
        "https://api.lever.co/v0/postings/acme",
    }


# --- fetch(): partial failure (one company down, others still succeed) ------


async def test_lever_fetch_skips_company_that_404s_and_continues(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/postings/ro" in str(request.url):
            return httpx.Response(200, json=[_RO_POSTING_1])
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [_RO, CompanyConfig(slug="not-a-real-company-xyz", company="Nobody")]
    scraper = LeverScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with caplog.at_level(logging.WARNING):
        async with scraper.http:
            raw = await scraper.fetch()

    assert list(raw.keys()) == ["ro"]
    assert len(transport.calls) == 2  # both companies attempted, no live calls
    assert any("not-a-real-company-xyz" in record.message for record in caplog.records)


async def test_lever_fetch_raises_scraper_error_when_all_companies_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    companies = [
        CompanyConfig(slug="not-a-real-company-1", company="Nobody One"),
        CompanyConfig(slug="not-a-real-company-2", company="Nobody Two"),
    ]
    scraper = LeverScraper(
        companies=companies,
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()

    assert len(transport.calls) == 2  # both attempted before raising, no live calls


async def test_lever_fetch_raises_scraper_error_when_the_single_configured_company_fails() -> (
    None
):
    """`boards.json` configures exactly one Lever company ("ro") today --
    the "all configured companies fail" path must still be exercised (and
    still raise) when N == 1, not just when there happen to be several."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = _RecordingTransport(handler)
    scraper = LeverScraper(
        companies=[_RO],
        transport=transport,
        rate_limit_seconds=0,
        backoff_base_seconds=0.01,
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()

    assert len(transport.calls) == 1  # the one configured company was attempted, no live calls


# --- fetch(): malformed / unexpected response shape --------------------------


async def test_lever_fetch_skips_company_with_unexpected_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/postings/ro" in str(request.url):
            return httpx.Response(200, json=[_RO_POSTING_1])
        # acme responds 200 but with a shape that isn't a bare array at
        # all -- e.g. an upstream error payload -- must not crash.
        return httpx.Response(200, json={"error": "unexpected"})

    transport = _RecordingTransport(handler)
    scraper = LeverScraper(
        companies=[_RO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["ro"]
    assert len(transport.calls) == 2


async def test_lever_fetch_skips_company_with_invalid_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/postings/ro" in str(request.url):
            return httpx.Response(200, json=[_RO_POSTING_1])
        return httpx.Response(200, content=b"not json at all {{{")

    transport = _RecordingTransport(handler)
    scraper = LeverScraper(
        companies=[_RO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert list(raw.keys()) == ["ro"]
    assert len(transport.calls) == 2


# --- fetch(): empty job list for a company is valid, not an error -----------


async def test_lever_fetch_treats_empty_posting_list_as_valid_not_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/postings/ro" in str(request.url):
            return httpx.Response(200, json=[_RO_POSTING_1])
        return httpx.Response(200, json=[])  # acme has zero openings today

    transport = _RecordingTransport(handler)
    scraper = LeverScraper(
        companies=[_RO, _ACME],
        transport=transport,
        rate_limit_seconds=0,
    )

    async with scraper.http:
        raw = await scraper.fetch()

    assert raw == {"ro": [_RO_POSTING_1], "acme": []}
    jobs = scraper.parse(raw)
    assert len(jobs) == 1
    assert len(transport.calls) == 2
