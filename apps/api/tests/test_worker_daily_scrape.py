"""Tests for the daily scrape job (app/worker.py).

`app.worker` resolves `REDIS_URL` at import time (see test_worker.py's own
docstring for why) -- so, same as that file, `app.worker` is imported
inside each test body, after the `_env` autouse fixture has set env vars,
never at module top-level.

`FakeClient`/`FakeTable` (tests/fakes.py) stand in for the Supabase service-
role client -- no real Postgres/Redis in these tests. Scrapers are replaced
with `_FakeScraper` stand-ins (a bare async `.run()`), not real scraper
classes with mocked HTTP transports -- each scraper's own HTTP behavior is
already covered by its own test file; these tests are about the
orchestration around them (partial-board-failure isolation, dedup actually
running, scoring actually gating `job_matches`).
"""

from __future__ import annotations

from datetime import UTC

import pytest
from app.scrapers.base import PermanentlyExcludedSourceError, ScraperError
from app.scrapers.dedup import compute_dedup_hash
from app.scrapers.schemas import NormalizedJob

from tests.fakes import FakeClient
from tests.helpers import make_preferences_row, make_profile_row

_ALL_BOARDS = (
    "greenhouse",
    "lever",
    "workable",
    "remoteok",
    "web3career",
    "cryptojobslist",
    "linkedin",
)


class _FakeScraper:
    def __init__(
        self, jobs: list[NormalizedJob] | None = None, error: Exception | None = None
    ) -> None:
        self._jobs = jobs or []
        self._error = error

    async def run(self) -> list[NormalizedJob]:
        if self._error is not None:
            raise self._error
        return self._jobs


def _job(
    *,
    source_board: str = "greenhouse",
    title: str = "Backend Developer",
    company: str = "Acme",
    apply_url: str = "https://example.com/jobs/1",
    location: str | None = None,
    description: str = "A great opportunity.",
) -> NormalizedJob:
    return NormalizedJob(
        source_board=source_board,  # type: ignore[arg-type]
        title=title,
        company=company,
        location=location,
        description=description,
        apply_url=apply_url,
    )


def _registry_of_one_job_per_board() -> dict:
    return {
        board: _FakeScraper(jobs=[_job(source_board=board, apply_url=f"https://example.com/{board}")])
        for board in _ALL_BOARDS
    }


# --- happy path: all boards succeed ------------------------------------------


async def test_all_boards_succeed_happy_path(_env: None) -> None:
    from app.worker import run_daily_scrape

    registry = _registry_of_one_job_per_board()
    client = FakeClient()

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["scraped"] == 7
    assert result["new"] == 7
    assert result["jobs_inserted"] == 7
    assert result["matches_created"] == 0  # no users configured
    assert len(client.table("jobs").rows) == 7


# --- one board failing does not stop the others ------------------------------


async def test_one_board_failing_does_not_stop_others(_env: None) -> None:
    from app.worker import run_daily_scrape

    registry = _registry_of_one_job_per_board()
    registry["linkedin"] = _FakeScraper(error=PermanentlyExcludedSourceError("no access"))
    client = FakeClient()

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["scraped"] == 6
    assert result["jobs_inserted"] == 6


async def test_every_board_failing_still_does_not_raise(_env: None) -> None:
    from app.worker import run_daily_scrape

    registry = {board: _FakeScraper(error=ScraperError("down")) for board in _ALL_BOARDS}
    client = FakeClient()

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["scraped"] == 0
    assert result["jobs_inserted"] == 0


# --- dedup is actually invoked, not bypassed ---------------------------------


async def test_dedup_drops_job_already_in_db(_env: None) -> None:
    from app.worker import run_daily_scrape

    already_scraped = _job(title="Backend Engineer", company="Acme")
    existing_row = {"dedup_hash": compute_dedup_hash(already_scraped)}
    client = FakeClient(jobs=[existing_row])

    registry = {
        "greenhouse": _FakeScraper(jobs=[already_scraped]),
        "lever": _FakeScraper(jobs=[_job(source_board="lever", apply_url="https://example.com/new")]),
    }

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["scraped"] == 2
    assert result["new"] == 1
    assert result["jobs_inserted"] == 1


async def test_dedup_drops_in_batch_duplicate_across_boards(_env: None) -> None:
    from app.worker import run_daily_scrape

    same_job_a = _job(source_board="greenhouse", title="Backend Engineer", company="Acme")
    same_job_b = _job(source_board="lever", title="Backend Engineer", company="Acme")
    client = FakeClient()

    registry = {
        "greenhouse": _FakeScraper(jobs=[same_job_a]),
        "lever": _FakeScraper(jobs=[same_job_b]),
    }

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["scraped"] == 2
    assert result["new"] == 1
    assert result["jobs_inserted"] == 1


# --- scoring is actually invoked and gates job_matches by threshold ---------


async def test_scoring_gates_job_matches_by_threshold(_env: None) -> None:
    from app.worker import run_daily_scrape

    profile_row = make_profile_row()  # default skills=["Python"], experience_level="junior"
    preferences_row = make_preferences_row()  # default match_score_threshold=2.0
    client = FakeClient(profiles=[profile_row], preferences=[preferences_row])

    high_scoring = _job(
        source_board="greenhouse",
        title="Python Developer",
        apply_url="https://example.com/high",
    )
    low_scoring = _job(
        source_board="lever",
        title="Ruby Developer",
        apply_url="https://example.com/low",
    )
    registry = {
        "greenhouse": _FakeScraper(jobs=[high_scoring]),
        "lever": _FakeScraper(jobs=[low_scoring]),
    }

    result = await run_daily_scrape({"job_try": 1}, scrapers=registry, client=client)

    assert result["jobs_inserted"] == 2
    assert result["matches_created"] == 1
    match_rows = client.table("job_matches").rows
    assert len(match_rows) == 1
    matched_job_id = match_rows[0]["job_id"]
    matched_job = next(r for r in client.table("jobs").rows if r["id"] == matched_job_id)
    assert matched_job["title"] == "Python Developer"


# --- retry/backoff: hand-rolled on top of ARQ's max_tries --------------------


async def test_unexpected_failure_raises_retry_with_exponential_backoff(
    _env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.worker as worker_module

    async def _boom(*args, **kwargs):
        raise RuntimeError("infra blip")

    monkeypatch.setattr(worker_module, "_fetch_all_users", _boom)

    with pytest.raises(worker_module.Retry) as exc_info:
        await worker_module.run_daily_scrape(
            {"job_try": 2}, scrapers={}, client=FakeClient()
        )

    expected_backoff_seconds = worker_module._RETRY_BACKOFF_BASE_SECONDS * (2 ** (2 - 1))
    assert exc_info.value.defer_score == pytest.approx(expected_backoff_seconds * 1000)


# --- schedule/config: confirmed at the ARQ job level, not hand-rolled -------


def test_daily_scrape_is_scheduled_at_0600_utc_with_max_3_tries(_env: None) -> None:
    import app.worker as worker_module

    assert worker_module.WorkerSettings.timezone is UTC

    cron_jobs = worker_module.WorkerSettings.cron_jobs
    assert len(cron_jobs) == 1
    job = cron_jobs[0]
    assert job.hour == 6
    assert job.minute == 0
    assert job.max_tries == worker_module._DAILY_SCRAPE_MAX_TRIES == 3
