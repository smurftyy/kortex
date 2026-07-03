"""Tests for CryptojobslistScraper.

Fail-closed by design (see app/scrapers/cryptojobslist.py's module docstring
and docs/superpowers/specs/2026-07-03-cryptojobslist-scraper-design.md): live
investigation found every content path (HTML pages, sitemap, the linked RSS
feed) behind Cloudflare bot management that challenges plain HTTP clients, the
same headless-browser-tooling gap app/scrapers/linkedin.py already flagged.
There is no live-shaped fetch/parse path to test field mapping or partial
failure against -- these tests instead assert the fail-closed contract
deterministically, mirroring test_scraper_linkedin.py's categories.
"""

from __future__ import annotations

import pytest
from app.scrapers.base import PermanentlyExcludedSourceError, ScraperError
from app.scrapers.cryptojobslist import (
    CryptojobslistHeadlessBrowserRequiredError,
    CryptojobslistScraper,
)


def test_source_board_is_cryptojobslist() -> None:
    assert CryptojobslistScraper.source_board == "cryptojobslist"


async def test_fetch_raises_headless_browser_required() -> None:
    scraper = CryptojobslistScraper()

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError):
        await scraper.fetch()


async def test_fetch_never_calls_the_http_client() -> None:
    scraper = CryptojobslistScraper()

    async def _fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("CryptojobslistScraper.fetch() must never call self.http.get()")

    scraper.http.get = _fail_if_called  # type: ignore[assignment]

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError):
        await scraper.fetch()


async def test_run_raises_headless_browser_required() -> None:
    scraper = CryptojobslistScraper()

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError):
        await scraper.run()


def test_parse_raises_headless_browser_required_for_arbitrary_input() -> None:
    scraper = CryptojobslistScraper()

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError):
        scraper.parse([{"anything": "goes"}])

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError):
        scraper.parse(None)


def test_headless_browser_required_is_permanently_excluded_and_not_retriable() -> None:
    scraper = CryptojobslistScraper()

    with pytest.raises(CryptojobslistHeadlessBrowserRequiredError) as exc_info:
        scraper.parse([])

    error = exc_info.value
    assert isinstance(error, PermanentlyExcludedSourceError)
    assert isinstance(error, ScraperError)
    assert error.retriable is False


def test_accepts_transport_and_headers_like_every_other_scraper() -> None:
    """Inherited from BaseScraper.__init__ -- inert here (fetch() never
    reaches self.http), but the constructor shape must still match every
    other scraper's so a caller doesn't need a special case for this one."""

    scraper = CryptojobslistScraper(headers={"User-Agent": "x"}, transport=None)

    assert scraper.http._headers == {"User-Agent": "x"}
