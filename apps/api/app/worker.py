"""ARQ worker.

`ping` (Commit 6) still exists purely to prove enqueue -> pickup ->
completion works end-to-end against a real Redis. The daily scrape job
below is Phase 2's real task logic, now that all 7 board scrapers
(app/scrapers/*.py), dedup (app/scrapers/dedup.py), and scoring
(app/scrapers/scoring.py) exist.

This is deliberately still one module, not a new `app/workers/` package —
the task that requested this cited a path of "apps/api/app/workers/", but
this codebase already has exactly one ARQ entrypoint
(``arq app.worker.WorkerSettings``, see README.md) and exactly one
``WorkerSettings`` class; splitting into a new package would mean either a
second, competing ``WorkerSettings`` (two ARQ setups) or a
`workers/__init__.py` that just re-exports this module, which adds a layer
without changing what's registered. Extending the existing module is the
literal reading of "reuse the existing ARQ setup, don't create a second
one" from the same task.

Run with: ``arq app.worker.WorkerSettings`` (see README.md).

## "Score against every user" — MVP scope, not paginated

Kortex is a single/small-user-count personal job-hunting tool at this
phase (no admin UI, no multi-tenant signup flow yet) — `_fetch_all_users`
loads every `profiles`/`preferences` row in one query, no batching or
pagination. This is a real scale limit (an unbounded `select("*")` against
every user), explicitly not the right call once the user count grows past
what fits comfortably in one query/one worker run — flagged here rather
than silently assumed to scale, so it's easy to find when it needs
revisiting (page through `profiles` in chunks, most likely).

## PRD 5.2: "Scraper failures should not crash the system — each board
## runs independently"

`_run_all_boards` runs every configured board *concurrently*
(`asyncio.gather`, not sequentially) and catches `ScraperError` per board —
this includes `PermanentlyExcludedSourceError` (LinkedIn, Cryptojobslist),
since it's a `ScraperError` subclass and needs no special-casing to avoid
stopping the run; that's exactly what that error type exists for (see
`app/scrapers/base.py`'s own docstring). A board's HTTP calls being
concurrent with the others doesn't violate any board's own rate limit —
each scraper owns an independent `RateLimiter` instance (`app/scrapers/
http.py`), scoped to that one instance's own requests, not shared/global.

## PRD 5.2: "Worker jobs retried up to 3 times with exponential backoff"

This is *not* automatic just from ARQ's `max_tries` — confirmed by reading
`arq.worker.Worker.run_job`: a job that raises a plain exception is marked
failed and NOT retried; only `arq.worker.Retry` (or a cancellation) is
retried. `max_tries` only caps *how many times* a `Retry`-driven re-run can
happen — the actual "catch the failure and back off" behavior has to be
raised explicitly, which `run_daily_scrape` does in its outer `except`.
This only wraps genuinely unexpected failures (a DB write erroring, a bug)
— per-board scraper failures are already caught and logged inside
`_run_all_boards` and never reach this handler, since those are each
board's own established partial-failure contract, not an infra failure of
the job itself.

## Scheduled for 06:00 UTC daily

`arq.cron.cron(..., hour=6, minute=0)` alone is not enough: `arq.worker.
Worker`'s cron evaluation defaults to the *host's local system timezone*
(`datetime.now().astimezone().tzinfo`) when `timezone` isn't set — confirmed
by reading `Worker.__init__`. `WorkerSettings.timezone = UTC` below is
required for "hour=6" to actually mean 06:00 UTC regardless of what
timezone the machine running the worker happens to be in.

## "Notify" hook

There's no digest/notification sender in this codebase yet (Phase 3,
per SCHEMA_kortex.md's own "Notes / Open Decisions" section). Nothing is
stubbed here for it: a `job_matches` row's own columns already are that
hook's future input verbatim (`notified_at TIMESTAMPTZ` — "when included in
a digest email", left `NULL` by every insert here since nothing has
notified anyone yet). Inventing a placeholder `notify()` function with no
schema-backed meaning would be an abstraction with nothing behind it;
"score above threshold creates the `job_matches` row Phase 3 will query" is
the real notify hook, this task's job.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC
from typing import Any

from arq.connections import RedisSettings
from arq.cron import cron
from arq.worker import Retry

from app.core.config import get_settings
from app.core.supabase import get_service_client
from app.schemas.preferences import PreferencesResponse
from app.schemas.profile import ProfileResponse
from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.cryptojobslist import CryptojobslistScraper
from app.scrapers.dedup import compute_dedup_hash, dedupe_against_existing
from app.scrapers.greenhouse import GreenhouseScraper
from app.scrapers.lever import LeverScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.schemas import NormalizedJob
from app.scrapers.scoring import score_job
from app.scrapers.web3career import Web3CareerScraper
from app.scrapers.workable import WorkableScraper

logger = logging.getLogger(__name__)

_DAILY_SCRAPE_MAX_TRIES = 3
_RETRY_BACKOFF_BASE_SECONDS = 30.0
_DAILY_SCRAPE_TIMEOUT_SECONDS = 1200.0  # 20 min -- 7 rate-limited boards run concurrently


async def ping(ctx: dict[str, Any]) -> str:
    """No-op health-check task."""

    return "pong"


def _build_scraper_registry() -> dict[str, BaseScraper | None]:
    """The real 7-board registry. `None` means "not configured" (currently
    only possible for Web3.career, which needs a signup-obtained API token
    — see `app/core/config.py`) — distinct from a board that's configured
    but fails; `_run_all_boards` logs and skips either case the same way.
    """

    settings = get_settings()
    registry: dict[str, BaseScraper | None] = {
        "greenhouse": GreenhouseScraper(),
        "lever": LeverScraper(),
        "workable": WorkableScraper(),
        "remoteok": RemoteOKScraper(),
        "cryptojobslist": CryptojobslistScraper(),
        "linkedin": LinkedInScraper(),
        "web3career": (
            Web3CareerScraper(api_token=settings.WEB3CAREER_API_TOKEN)
            if settings.WEB3CAREER_API_TOKEN
            else None
        ),
    }
    return registry


async def _run_all_boards(scrapers: dict[str, BaseScraper | None]) -> list[NormalizedJob]:
    """See module docstring's PRD 5.2 section: every board runs
    concurrently and independently; a board's total failure (including a
    deliberate `PermanentlyExcludedSourceError` exclusion) is logged and
    skipped, never stops another board, and never raises out of here.
    """

    active = {board: scraper for board, scraper in scrapers.items() if scraper is not None}
    for board, scraper in scrapers.items():
        if scraper is None:
            logger.warning("skipping board %r: not configured", board)

    results = await asyncio.gather(
        *(scraper.run() for scraper in active.values()), return_exceptions=True
    )

    jobs: list[NormalizedJob] = []
    for board, result in zip(active.keys(), results, strict=True):
        if isinstance(result, ScraperError):
            logger.warning("board %r failed entirely, skipping: %s", board, result)
        elif isinstance(result, BaseException):
            raise result
        else:
            jobs.extend(result)
    return jobs


async def _fetch_all_users(client: Any) -> list[tuple[ProfileResponse, PreferencesResponse]]:
    """See module docstring's "score against every user" section for why
    this doesn't paginate at this project's current scale."""

    profiles_result = await client.table("profiles").select("*").execute()
    preferences_result = await client.table("preferences").select("*").execute()

    profile_rows = profiles_result.data if isinstance(profiles_result.data, list) else []
    preference_rows = preferences_result.data if isinstance(preferences_result.data, list) else []
    preferences_by_user_id = {
        row["user_id"]: row for row in preference_rows if isinstance(row, dict)
    }

    pairs: list[tuple[ProfileResponse, PreferencesResponse]] = []
    for row in profile_rows:
        if not isinstance(row, dict):
            continue
        preference_row = preferences_by_user_id.get(row["id"])
        if preference_row is None:
            logger.warning(
                "profile %r has no preferences row -- skipping for scoring", row.get("id")
            )
            continue
        pairs.append((ProfileResponse(**row), PreferencesResponse(**preference_row)))
    return pairs


async def _persist_new_jobs_and_matches(
    client: Any,
    jobs: list[NormalizedJob],
    user_pairs: list[tuple[ProfileResponse, PreferencesResponse]],
) -> dict[str, int]:
    """Every surviving (already-deduped) job is inserted into `jobs`
    unconditionally -- that table is the shared, public listing set, not
    scoped to any one user's preferences. `job_matches` rows are created
    per user only when `score_job(...)` clears that user's own
    `match_score_threshold` -- see module docstring's "Notify hook"
    section for why nothing else happens with a match beyond that insert.
    """

    jobs_inserted = 0
    matches_created = 0

    for job in jobs:
        row = {
            "source_board": job.source_board,
            "external_id": job.external_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "stack_tags": job.stack_tags,
            "apply_url": job.apply_url,
            "dedup_hash": compute_dedup_hash(job),
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        }
        insert_result = await client.table("jobs").insert(row).execute()
        inserted_rows = insert_result.data if isinstance(insert_result.data, list) else []
        if not inserted_rows:
            continue
        jobs_inserted += 1
        job_id = inserted_rows[0]["id"]

        for profile, preferences in user_pairs:
            score = score_job(job, profile, preferences)
            if score > preferences.match_score_threshold:
                await client.table("job_matches").insert(
                    {"user_id": str(profile.id), "job_id": job_id, "match_score": score}
                ).execute()
                matches_created += 1

    return {"jobs_inserted": jobs_inserted, "matches_created": matches_created}


async def run_daily_scrape(
    ctx: dict[str, Any],
    *,
    scrapers: dict[str, BaseScraper | None] | None = None,
    client: Any = None,
) -> dict[str, int]:
    """The Commit 17 daily scrape job: run every board, dedupe, score
    against every user, persist. See the module docstring for every
    scoping/resilience/retry decision this makes.

    `scrapers`/`client` are injectable for tests (defaulting to the real
    7-board registry / a real service-role Supabase client when omitted) —
    same dependency-injection pattern `BaseScraper`'s own `transport`
    parameter already uses.
    """

    try:
        active_scrapers = scrapers if scrapers is not None else _build_scraper_registry()
        active_client = client if client is not None else await get_service_client()

        raw_jobs = await _run_all_boards(active_scrapers)
        new_jobs = await dedupe_against_existing(raw_jobs, active_client)
        user_pairs = await _fetch_all_users(active_client)
        persisted = await _persist_new_jobs_and_matches(active_client, new_jobs, user_pairs)

        return {"scraped": len(raw_jobs), "new": len(new_jobs), **persisted}
    except Exception as exc:
        job_try = ctx.get("job_try", 1)
        backoff_seconds = _RETRY_BACKOFF_BASE_SECONDS * (2 ** (job_try - 1))
        logger.exception(
            "daily scrape job failed (try %d), retrying in %.1fs", job_try, backoff_seconds
        )
        raise Retry(defer=backoff_seconds) from exc


class WorkerSettings:
    """Entrypoint class for the ``arq`` CLI (``arq app.worker.WorkerSettings``)."""

    functions = [ping]
    cron_jobs = [
        cron(
            run_daily_scrape,
            hour=6,
            minute=0,
            max_tries=_DAILY_SCRAPE_MAX_TRIES,
            timeout=_DAILY_SCRAPE_TIMEOUT_SECONDS,
        )
    ]
    # Required so "hour=6" above means 06:00 UTC regardless of the host
    # machine's own timezone -- see module docstring.
    timezone = UTC
    redis_settings = RedisSettings.from_dsn(get_settings().REDIS_URL)
