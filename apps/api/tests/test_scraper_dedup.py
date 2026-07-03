"""Tests for job deduplication (app/scrapers/dedup.py).

See that module's docstring for the normalization/hashing/collision
decisions this exercises. `FakeClient`/`FakeTable` (tests/fakes.py) stand in
for the Supabase client for the DB-checking half -- no real Postgres in
these tests, same convention as test_jobs.py.
"""

from __future__ import annotations

from app.scrapers.dedup import (
    compute_dedup_hash,
    dedupe_against_existing,
    dedupe_batch,
)
from app.scrapers.schemas import NormalizedJob

from tests.fakes import FakeClient


def _job(
    *,
    title: str = "Senior Backend Engineer",
    company: str = "Acme",
    apply_url: str = "https://boards.greenhouse.io/acme/jobs/123",
    source_board: str = "greenhouse",
    description: str = "d",
) -> NormalizedJob:
    return NormalizedJob(
        source_board=source_board,  # type: ignore[arg-type]
        title=title,
        company=company,
        description=description,
        apply_url=apply_url,
    )


# --- compute_dedup_hash(): normalization -------------------------------------


def test_identical_jobs_hash_the_same() -> None:
    a = _job()
    b = _job()

    assert compute_dedup_hash(a) == compute_dedup_hash(b)


def test_whitespace_and_casing_differences_hash_the_same() -> None:
    a = _job(title="Senior Backend Engineer", company="Acme")
    b = _job(title="  senior   backend engineer ", company="ACME")

    assert compute_dedup_hash(a) == compute_dedup_hash(b)


def test_tracking_query_params_do_not_change_the_hash() -> None:
    a = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
    b = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123?utm_source=api&ref=xyz")

    assert compute_dedup_hash(a) == compute_dedup_hash(b)


def test_trailing_slash_does_not_change_the_hash() -> None:
    a = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
    b = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123/")

    assert compute_dedup_hash(a) == compute_dedup_hash(b)


def test_host_case_does_not_change_the_hash() -> None:
    a = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
    b = _job(apply_url="https://BOARDS.GREENHOUSE.IO/acme/jobs/123")

    assert compute_dedup_hash(a) == compute_dedup_hash(b)


def test_different_path_produces_a_different_hash() -> None:
    a = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
    b = _job(apply_url="https://boards.greenhouse.io/acme/jobs/456")

    assert compute_dedup_hash(a) != compute_dedup_hash(b)


def test_genuinely_different_jobs_do_not_collide() -> None:
    a = _job(title="Backend Engineer", company="Acme")
    b = _job(title="Frontend Engineer", company="Acme")
    c = _job(title="Backend Engineer", company="Globex")

    hashes = {compute_dedup_hash(a), compute_dedup_hash(b), compute_dedup_hash(c)}
    assert len(hashes) == 3


def test_hash_is_stable_across_calls() -> None:
    """Not Python's salted built-in hash() -- must be reproducible across
    processes/runs, since it's stored in a UNIQUE DB column."""

    job = _job()

    assert compute_dedup_hash(job) == compute_dedup_hash(job)


# --- dedupe_batch(): in-memory, first-seen wins ------------------------------


def test_dedupe_batch_drops_exact_duplicate() -> None:
    a = _job(source_board="greenhouse")
    b = _job(source_board="lever")  # same title/company/url, different source

    result = dedupe_batch([a, b])

    assert result == [a]


def test_dedupe_batch_drops_whitespace_and_casing_variant() -> None:
    a = _job(title="Senior Backend Engineer", company="Acme")
    b = _job(title="  SENIOR BACKEND ENGINEER  ", company="acme")

    result = dedupe_batch([a, b])

    assert result == [a]


def test_dedupe_batch_drops_tracking_param_variant() -> None:
    a = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
    b = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123?utm_source=api")

    result = dedupe_batch([a, b])

    assert result == [a]


def test_dedupe_batch_keeps_genuinely_different_jobs() -> None:
    a = _job(title="Backend Engineer")
    b = _job(title="Frontend Engineer")

    result = dedupe_batch([a, b])

    assert result == [a, b]


def test_dedupe_batch_is_empty_for_empty_input() -> None:
    assert dedupe_batch([]) == []


# --- dedupe_against_existing(): DB-aware -------------------------------------


async def test_dedupe_against_existing_drops_job_already_in_db() -> None:
    existing_job = _job(title="Backend Engineer", company="Acme")
    existing_row = {"dedup_hash": compute_dedup_hash(existing_job)}
    client = FakeClient(jobs=[existing_row])

    new_job = _job(title="Frontend Engineer", company="Acme")
    scraped = [existing_job, new_job]

    result = await dedupe_against_existing(scraped, client)

    assert result == [new_job]


async def test_dedupe_against_existing_matches_db_row_despite_tracking_param_difference() -> None:
    existing_row = {
        "dedup_hash": compute_dedup_hash(
            _job(apply_url="https://boards.greenhouse.io/acme/jobs/123")
        )
    }
    client = FakeClient(jobs=[existing_row])

    scraped_again = _job(apply_url="https://boards.greenhouse.io/acme/jobs/123?utm_source=api")

    result = await dedupe_against_existing([scraped_again], client)

    assert result == []


async def test_dedupe_against_existing_keeps_job_not_in_db() -> None:
    client = FakeClient(jobs=[{"dedup_hash": "some-other-hash"}])
    new_job = _job()

    result = await dedupe_against_existing([new_job], client)

    assert result == [new_job]


async def test_dedupe_against_existing_also_applies_in_batch_dedup() -> None:
    client = FakeClient(jobs=[])
    a = _job(source_board="greenhouse")
    b = _job(source_board="lever")  # duplicate of a

    result = await dedupe_against_existing([a, b], client)

    assert result == [a]


async def test_dedupe_against_existing_handles_empty_batch_without_querying() -> None:
    client = FakeClient(jobs=[])

    result = await dedupe_against_existing([], client)

    assert result == []
