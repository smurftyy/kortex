"""Tests for Web3CareerScraper.

All HTTP in this file is mocked via `httpx.MockTransport` with fixture JSON
dicts shaped like Web3.career's documented OpenAPI response (see
docs/superpowers/specs/2026-07-03-web3career-scraper-design.md) -- no token
was available to validate against the live API, so unlike RemoteOK/
Greenhouse/Lever/Workable there is no live end-to-end test here, only
mocked coverage against the spec's documented schema. `_RecordingTransport`
records every request it resolves so "no live network calls" is asserted
on directly, matching test_scraper_lever.py's pattern.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from app.scrapers.base import ScraperError
from app.scrapers.schemas import NormalizedJob
from app.scrapers.web3career import Web3CareerScraper


class _RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.calls: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self._handler(request)


_JOB_1: dict[str, Any] = {
    "id": "job_7f3a2c9b",
    "title": "Senior Solidity Developer",
    "company": "ChainForge Labs",
    "location": "Remote",
    "remote": True,
    "description": "<p>Build and audit smart contracts.</p>",
    "tags": ["solidity", "smart-contract"],
    "apply_url": "https://web3.career/apply/7f3a2c9b?utm_source=api&ref=x",
    "url": "https://web3.career/jobs/7f3a2c9b",
    "salary": "$120k-$180k",
    "postedAt": "2026-06-18",
}

_JOB_2: dict[str, Any] = {
    "id": "job_3c91a0e1",
    "title": "Smart Contract Auditor",
    "company": "VeriBridge Security",
    "location": "Berlin, Germany",
    "remote": False,
    "description": "<p>Audit DeFi protocols.</p>",
    "tags": ["security", "defi"],
    "apply_url": "https://web3.career/apply/3c91a0e1?utm_source=api&ref=x",
    "url": "https://web3.career/jobs/3c91a0e1",
    "postedAt": "2026-06-25",
}


# --- parse(): field mapping ---------------------------------------------------


def test_web3career_parse_maps_all_fields() -> None:
    scraper = Web3CareerScraper(api_token="tok")

    jobs = scraper.parse([_JOB_1])

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_board == "web3career"
    assert job.external_id == "job_7f3a2c9b"
    assert job.title == "Senior Solidity Developer"
    assert job.company == "ChainForge Labs"
    assert job.location == "Remote"
    assert job.description == "<p>Build and audit smart contracts.</p>"
    assert job.stack_tags == ["solidity", "smart-contract"]
    assert job.apply_url == "https://web3.career/apply/7f3a2c9b?utm_source=api&ref=x"
    assert job.posted_at is not None
    assert job.posted_at.year == 2026
    assert job.posted_at.month == 6
    assert job.posted_at.day == 18


def test_web3career_appends_remote_suffix_when_location_does_not_already_say_remote() -> None:
    scraper = Web3CareerScraper(api_token="tok")
    job = {**_JOB_1, "location": "Austin, TX", "remote": True}

    jobs = scraper.parse([job])

    assert jobs[0].location == "Austin, TX (Remote)"


def test_web3career_does_not_duplicate_remote_when_location_already_says_remote() -> None:
    scraper = Web3CareerScraper(api_token="tok")
    job = {**_JOB_1, "location": "Remote", "remote": True}

    jobs = scraper.parse([job])

    assert jobs[0].location == "Remote"


def test_web3career_handles_unparseable_posted_at_by_leaving_it_none() -> None:
    scraper = Web3CareerScraper(api_token="tok")
    job = {**_JOB_1, "postedAt": "3 days ago"}

    jobs = scraper.parse([job])

    assert len(jobs) == 1
    assert jobs[0].posted_at is None


def test_web3career_missing_postedat_leaves_it_none() -> None:
    scraper = Web3CareerScraper(api_token="tok")
    job = {k: v for k, v in _JOB_1.items() if k != "postedAt"}

    jobs = scraper.parse([job])

    assert jobs[0].posted_at is None


# --- parse(): malformed listing skipped, not fatal ----------------------------


def test_web3career_parse_skips_listing_missing_required_field_without_raising(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scraper = Web3CareerScraper(api_token="tok")
    bad_job = {k: v for k, v in _JOB_1.items() if k != "title"}  # missing required field
    bad_job["id"] = "job_bad"

    with caplog.at_level(logging.WARNING):
        jobs = scraper.parse([_JOB_1, bad_job, _JOB_2])

    assert len(jobs) == 2
    assert {job.external_id for job in jobs} == {"job_7f3a2c9b", "job_3c91a0e1"}
    assert any("job_bad" in record.message for record in caplog.records)


def test_web3career_parse_returns_empty_list_for_empty_job_array() -> None:
    scraper = Web3CareerScraper(api_token="tok")

    jobs = scraper.parse([])

    assert jobs == []


# --- fetch()+run(): happy path -------------------------------------------------


async def test_web3career_happy_path_fetch_parse_normalize() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["token"] == "tok"
        return httpx.Response(200, json=["ok", "v1", [_JOB_1, _JOB_2]])

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="tok", transport=transport, rate_limit_seconds=0)

    jobs = await scraper.run()

    assert len(jobs) == 2
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "web3career" for job in jobs)
    assert len(transport.calls) == 1
    assert str(transport.calls[0].url).startswith("https://web3.career/api/v1")


async def test_web3career_fetch_extracts_jobs_from_metadata_string_envelope() -> None:
    """Modal documented shape: [status_string, version_string, Job[]]."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["ok", "v1", [_JOB_1, _JOB_2]])

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="tok", transport=transport, rate_limit_seconds=0)

    async with scraper.http:
        raw = await scraper.fetch()

    assert raw == [_JOB_1, _JOB_2]


async def test_web3career_fetch_extracts_jobs_when_root_array_is_directly_the_job_list() -> None:
    """Documented fallback shape: no leading metadata strings at all."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_JOB_1, _JOB_2])

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="tok", transport=transport, rate_limit_seconds=0)

    async with scraper.http:
        raw = await scraper.fetch()

    assert raw == [_JOB_1, _JOB_2]


async def test_web3career_sends_honest_user_agent() -> None:
    scraper = Web3CareerScraper(api_token="tok")

    assert scraper.http._headers is not None
    assert "KortexBot" in scraper.http._headers["User-Agent"]


# --- fetch(): total failure -----------------------------------------------------


async def test_web3career_fetch_raises_scraper_error_on_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(
        api_token="tok", transport=transport, rate_limit_seconds=0, backoff_base_seconds=0.01
    )

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()


async def test_web3career_fetch_raises_scraper_error_on_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all {{{")

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="tok", transport=transport, rate_limit_seconds=0)

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()


async def test_web3career_fetch_raises_scraper_error_on_unexpected_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "nope"})

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="tok", transport=transport, rate_limit_seconds=0)

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()


async def test_web3career_fetch_raises_scraper_error_when_401_unauthorized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    transport = _RecordingTransport(handler)
    scraper = Web3CareerScraper(api_token="bad-token", transport=transport, rate_limit_seconds=0)

    with pytest.raises(ScraperError):
        async with scraper.http:
            await scraper.fetch()


def test_web3career_rate_limit_defaults_to_one_second() -> None:
    scraper = Web3CareerScraper(api_token="tok")

    assert scraper.http._rate_limiter is not None
    assert scraper.http._rate_limiter._min_interval == 1.0
