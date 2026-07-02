"""Live validation for RemoteOKScraper — hits the real API, no mocks.

Per this commit's validation standard: fetch -> parse -> normalize proven
against RemoteOK's actual current response, including the leading
legal/metadata notice entry that isn't a real listing (see app/scrapers/
remoteok.py's module docstring).
"""

from __future__ import annotations

from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.schemas import NormalizedJob


async def test_remoteok_live_fetch_parse_normalize_end_to_end() -> None:
    scraper = RemoteOKScraper(backoff_base_seconds=0.2)

    jobs = await scraper.run()

    assert len(jobs) > 0
    assert all(isinstance(job, NormalizedJob) for job in jobs)
    assert all(job.source_board == "remoteok" for job in jobs)
    assert all(job.title for job in jobs)
    assert all(job.company for job in jobs)
    assert all(job.description for job in jobs)
    assert all(job.apply_url.startswith("http") for job in jobs)
    # The feed's leading legal/metadata entry has no "position"/"company"/
    # etc. and must be dropped, not crash the whole parse.
    assert all(job.title != "" for job in jobs)


def test_remoteok_parse_skips_the_leading_legal_notice_entry() -> None:
    scraper = RemoteOKScraper()
    raw = [
        {"legal": "API Terms of Service: ...", "last_updated": 1234567890},
        {
            "id": "999",
            "position": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "desc",
            "tags": ["python"],
            "apply_url": "https://remoteok.com/remote-jobs/999",
            "date": "2026-01-01T00:00:00+00:00",
        },
    ]

    jobs = scraper.parse(raw)

    assert len(jobs) == 1
    assert jobs[0].external_id == "999"
    assert jobs[0].title == "Backend Engineer"


def test_remoteok_parse_skips_listing_missing_required_field_without_raising() -> None:
    scraper = RemoteOKScraper()
    raw = [
        {"id": "1", "position": "Good listing", "company": "Acme", "description": "d",
         "apply_url": "https://remoteok.com/remote-jobs/1", "tags": []},
        {"id": "2", "company": "Acme", "description": "d",
         "apply_url": "https://remoteok.com/remote-jobs/2", "tags": []},  # missing "position"
        {"id": "3", "position": "Another good one", "company": "Acme", "description": "d",
         "apply_url": "https://remoteok.com/remote-jobs/3", "tags": []},
    ]

    jobs = scraper.parse(raw)

    assert len(jobs) == 2
    assert {job.external_id for job in jobs} == {"1", "3"}


def test_remoteok_normalizes_stray_comma_in_location() -> None:
    scraper = RemoteOKScraper()
    raw = [
        {
            "id": "1",
            "position": "x",
            "company": "x",
            "description": "d",
            "apply_url": "https://remoteok.com/remote-jobs/1",
            "location": "San Salvador, ",
            "tags": [],
        }
    ]

    jobs = scraper.parse(raw)

    assert jobs[0].location == "San Salvador"


def test_remoteok_rate_limit_defaults_to_crawl_delay() -> None:
    scraper = RemoteOKScraper()

    assert scraper.http._rate_limiter is not None
    assert scraper.http._rate_limiter._min_interval == 1.0


def test_remoteok_sends_honest_user_agent() -> None:
    scraper = RemoteOKScraper()

    assert scraper.http._headers is not None
    assert "KortexBot" in scraper.http._headers["User-Agent"]
    assert "ClaudeBot" not in scraper.http._headers["User-Agent"]
