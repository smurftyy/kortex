"""Tests for job deduplication (app/scrapers/dedup.py).

See that module's docstring for the normalization/hashing/collision
decisions this exercises. `FakeClient`/`FakeTable` (tests/fakes.py) stand in
for the Supabase client for the DB-checking half -- no real Postgres in
these tests, same convention as test_jobs.py.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

from app.scrapers.dedup import (
    _HASH_CHUNK_SIZE,
    compute_dedup_hash,
    dedupe_against_existing,
    dedupe_batch,
    fetch_existing_dedup_hashes,
)
from app.scrapers.schemas import NormalizedJob

from tests.fakes import FakeClient


class _RecordingJobsTable:
    """Local to this test file (not tests/fakes.py) -- tracks every `.in_()`
    call's own batch, so a test can assert chunking actually happened, not
    just that the final unioned result was correct."""

    def __init__(self, existing_hashes: set[str]) -> None:
        self._existing_hashes = existing_hashes
        self._pending_in: list[str] | None = None
        self.calls: list[list[str]] = []

    def select(self, *_columns: str) -> _RecordingJobsTable:
        return self

    def in_(self, column: str, values: list[str]) -> _RecordingJobsTable:
        assert column == "dedup_hash"
        self._pending_in = list(values)
        return self

    async def execute(self) -> SimpleNamespace:
        assert self._pending_in is not None
        self.calls.append(self._pending_in)
        matched = [h for h in self._pending_in if h in self._existing_hashes]
        return SimpleNamespace(data=[{"dedup_hash": h} for h in matched])


class _RecordingClient:
    def __init__(self, existing_hashes: set[str]) -> None:
        self.jobs = _RecordingJobsTable(existing_hashes)

    def table(self, name: str) -> _RecordingJobsTable:
        assert name == "jobs"
        return self.jobs


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


# --- fetch_existing_dedup_hashes(): chunking large batches -------------------
#
# Regression test for the Phase 2 verification finding: a single `.in_()`
# call with a large hash list serializes into a query string that exceeds
# PostgREST/Kong's URL length limit (414 URI too long), confirmed live
# against ~500 real Greenhouse listings. `_RecordingClient` above tracks
# every individual call's own batch so this asserts chunking actually
# happened -- not just that the final unioned result was correct, which a
# single oversized call would also get right against a real DB (until it
# 414s) or a naive fake with no length limit.


def _synthetic_hashes(count: int) -> list[str]:
    return [hashlib.sha256(str(i).encode()).hexdigest() for i in range(count)]


async def test_fetch_existing_dedup_hashes_chunks_large_batches() -> None:
    hashes = _synthetic_hashes(550)
    # A mix of existing/new spread across what will become multiple chunks,
    # not just concentrated in the first one.
    existing_hashes = {hashes[0], hashes[99], hashes[100], hashes[250], hashes[549]}
    client = _RecordingClient(existing_hashes)

    result = await fetch_existing_dedup_hashes(client, hashes)

    assert result == existing_hashes


async def test_fetch_existing_dedup_hashes_issues_multiple_requests_not_one_oversized_one() -> (
    None
):
    hashes = _synthetic_hashes(550)
    client = _RecordingClient(existing_hashes=set())

    await fetch_existing_dedup_hashes(client, hashes)

    assert len(client.jobs.calls) > 1, "550 hashes must not be sent as a single .in_() call"
    assert len(client.jobs.calls) == -(-550 // _HASH_CHUNK_SIZE)  # ceil division
    for call in client.jobs.calls:
        assert len(call) <= _HASH_CHUNK_SIZE
    # Every hash requested exactly once, none dropped or duplicated across chunks.
    assert sorted(h for call in client.jobs.calls for h in call) == sorted(hashes)


async def test_fetch_existing_dedup_hashes_small_batch_is_still_one_request() -> None:
    """Chunking must not change behavior for the common case (a handful of
    hashes) -- one request, same as before this fix."""

    hashes = _synthetic_hashes(3)
    client = _RecordingClient(existing_hashes={hashes[0]})

    result = await fetch_existing_dedup_hashes(client, hashes)

    assert result == {hashes[0]}
    assert len(client.jobs.calls) == 1
