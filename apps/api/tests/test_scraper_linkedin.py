"""Tests for the Commit 14 LinkedIn scraper.

No live validation: LinkedInScraper is fail-closed by design (see
app/scrapers/linkedin.py's module docstring) and never makes a network
request, so there is no live path to validate. These tests instead assert
the fail-closed contract deterministically.
"""

from __future__ import annotations

import pytest
from app.scrapers.base import PermanentlyExcludedSourceError, ScraperError
from app.scrapers.linkedin import LinkedInAccessDeniedError, LinkedInScraper


def test_source_board_is_linkedin() -> None:
    assert LinkedInScraper.source_board == "linkedin"


async def test_fetch_raises_access_denied() -> None:
    scraper = LinkedInScraper()

    with pytest.raises(LinkedInAccessDeniedError):
        await scraper.fetch()


async def test_fetch_never_calls_the_http_client() -> None:
    scraper = LinkedInScraper()

    async def _fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("LinkedInScraper.fetch() must never call self.http.get()")

    scraper.http.get = _fail_if_called  # type: ignore[assignment]

    with pytest.raises(LinkedInAccessDeniedError):
        await scraper.fetch()


async def test_run_raises_access_denied() -> None:
    scraper = LinkedInScraper()

    with pytest.raises(LinkedInAccessDeniedError):
        await scraper.run()


def test_parse_raises_access_denied_for_arbitrary_input() -> None:
    scraper = LinkedInScraper()

    with pytest.raises(LinkedInAccessDeniedError):
        scraper.parse([{"anything": "goes"}])

    with pytest.raises(LinkedInAccessDeniedError):
        scraper.parse(None)


def test_access_denied_is_permanently_excluded_and_not_retriable() -> None:
    scraper = LinkedInScraper()

    with pytest.raises(LinkedInAccessDeniedError) as exc_info:
        scraper.parse([])

    error = exc_info.value
    assert isinstance(error, PermanentlyExcludedSourceError)
    assert isinstance(error, ScraperError)
    assert error.retriable is False
