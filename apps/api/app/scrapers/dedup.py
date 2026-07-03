"""Job deduplication.

`SCHEMA_kortex.md` section 4 / the `jobs` migration
(`apps/api/supabase/migrations/20260702000003_create_jobs.sql`) already
settle the shape of this: `dedup_hash TEXT NOT NULL UNIQUE`, comment
`hash(url + title + company)`. `NormalizedJob`'s own docstring
(`app/scrapers/schemas.py`) already earmarks this as "Commit 15" work —
this module is that commit. (Note: the task that requested this module cited
"PRD_kortex.md section 4.3" for the "Deduplicates by URL + title + company
hash" requirement; no file named `PRD_kortex.md` exists anywhere in this
repo. The requirement itself is real and already corroborated by
`SCHEMA_kortex.md` and the migration above, so this module proceeds on that
basis — flagging the missing/renamed source doc rather than silently
inventing content for a section that can't be found.)

## Normalization before hashing

Neither `SCHEMA_kortex.md` nor the migration specify normalization — "hash
(url + title + company)" reads as literal concatenation. Hashing the raw
strings verbatim would silently fail to catch the two most common ways the
*same* listing produces *different* raw text across scrapers/re-scrapes:

- **Case/whitespace drift**: "Senior Engineer" vs "senior engineer", or a
  stray double space from HTML-to-text extraction (several scrapers in this
  codebase concatenate HTML fragments into `description`/`title`-adjacent
  fields — see `LeverScraper`). `title`/`company` are lowercased and run
  through `" ".join(s.split())` (collapses any run of whitespace, including
  tabs/newlines, to a single space, and strips leading/trailing) before
  hashing.
- **URL tracking parameters**: Web3.career's `apply_url` ships with
  `utm_source`/`ref` params baked in *by the source itself* (see
  `app/scrapers/web3career.py`); a re-scrape of the same listing is not
  guaranteed to receive byte-identical tracking params every time. The query
  string and fragment are dropped entirely before hashing, and scheme/host
  are lowercased (case-insensitive per RFC 3986); the path is left exactly
  as given (URL paths *are* case-sensitive in general — lowercasing it could
  wrongly conflate two genuinely different pages on a case-sensitive
  server), except for a single trailing slash, which is stripped so
  `/jobs/123` and `/jobs/123/` hash identically.

This is a judgment call the source docs don't make explicitly — documented
here rather than silently baked in, since it changes what counts as "the
same job" versus what `apply_url`'s own docstring in `schemas.py` protects
against (it deliberately avoids pydantic's URL-normalizing `HttpUrl` type so
`apply_url` itself, as stored, stays byte-identical to what the source
returned — canonicalization here is scoped to hashing only, and never
mutates the stored `apply_url`).

## Hash algorithm

SHA-256 over the three normalized fields joined with `"|"` (a delimiter
prevents `("ab", "c")` and `("a", "bc")` from colliding). Python's built-in
`hash()` is deliberately not used — it's salted per-process
(`PYTHONHASHSEED`), so the same job would hash differently across scraper
runs/worker restarts, defeating the whole point of a stable dedup key stored
in a `UNIQUE` column.

## Collision resolution

- **Within one batch** (jobs from any/all scrapers in a single run,
  combined before this module sees them): first-seen wins, in input order.
  There's no meaningful signal to prefer one scraper's copy of the same
  listing over another's — `NormalizedJob` doesn't carry a "which source is
  more authoritative" flag, so "whichever came first in the combined list"
  is a stable, reproducible tiebreak rather than an arbitrary one to invent.
- **Against rows already in `jobs`** (from previous scrape runs): the
  existing DB row wins outright — a job whose hash is already present is
  dropped from the batch entirely, not merged or used to update the
  existing row. This module answers "which of these freshly-scraped jobs
  are new", nothing more; refreshing `posted_at`/toggling `is_active` for a
  listing that's gone stale requires comparing across runs over time, which
  `schemas.py`'s own docstring already scopes out as later lifecycle-
  management logic, not this module's job. Consequence: whatever inserts
  the surviving output of `dedupe_against_existing` can be a plain INSERT,
  never an upsert -- duplicates are filtered out beforehand.

## Chunking the "already in `jobs`" check (Phase 2 verification fix)

`fetch_existing_dedup_hashes` originally issued one `.in_("dedup_hash",
hashes)` call for the whole batch. That's a GET request whose filter value
is serialized into the URL's query string -- confirmed live during Phase 2
verification: running the real worker against ~500 real Greenhouse
listings produced a query string long enough that PostgREST/Kong (the
proxy fronting it, in this project's Supabase stack) returned `414 URI too
long`. The ARQ worker (`app/worker.py`) caught this and retried, but
retrying rebuilds the identical oversized request every time -- a
permanent failure disguised as a transient one.

`_HASH_CHUNK_SIZE = 100` is not arbitrary: Kong/nginx's default
`large_client_header_buffers` caps a request line at 8KB. Each
`dedup_hash` is a fixed 64-character hex SHA-256 digest
(`compute_dedup_hash`'s own output); serialized into `.in_()` as
`dedup_hash=in.(h1,h2,...)`, each hash contributes roughly 65 bytes (64
hex characters + one separator). 100 hashes is therefore ~6.5KB --
comfortably under the 8KB limit with about 1.5KB of headroom left for the
base URL, the `select=dedup_hash` parameter, and any client-side percent-
encoding, rather than cutting it close to the theoretical ~120-hash
maximum that 8KB alone would allow.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.scrapers.schemas import NormalizedJob

# See the module docstring's "Chunking..." section for why 100, specifically.
_HASH_CHUNK_SIZE = 100


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).lower()


def _canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def compute_dedup_hash(job: NormalizedJob) -> str:
    """The one place `hash(url + title + company)` (SCHEMA_kortex.md
    section 4) is actually computed -- see the module docstring for the
    normalization/algorithm decisions."""

    canonical = "|".join(
        [
            _canonicalize_url(job.apply_url),
            _normalize_text(job.title),
            _normalize_text(job.company),
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_pairs(jobs: Iterable[NormalizedJob]) -> list[tuple[str, NormalizedJob]]:
    return [(compute_dedup_hash(job), job) for job in jobs]


def dedupe_batch(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """De-dup a combined batch (any/all scrapers) in memory. First-seen
    wins -- see the module docstring's "Collision resolution" section.
    Does not touch the database; combine with `dedupe_against_existing` to
    also drop jobs already present in `jobs` from previous runs.
    """

    seen: set[str] = set()
    result: list[NormalizedJob] = []
    for dedup_hash, job in _hash_pairs(jobs):
        if dedup_hash in seen:
            continue
        seen.add(dedup_hash)
        result.append(job)
    return result


async def fetch_existing_dedup_hashes(client: Any, hashes: Iterable[str]) -> set[str]:
    """Query which of `hashes` already have a row in `jobs`.

    `client` is deliberately untyped beyond `Any`: it only needs to support
    the same `.table(...).select(...).in_(...).execute()` chain every other
    route in this codebase already uses against the real Supabase
    `AsyncClient` (see `app/api/routes/jobs.py`) -- `get_anon_client()` is
    sufficient here since reading `jobs.dedup_hash` needs no more privilege
    than the existing public `GET /jobs` route already has (no RLS on this
    table). This is the "minimum needed" query layer the task called for,
    not a jobs repository -- writing the surviving new rows is a separate,
    later concern (the worker/DB-write commit `app/worker.py` already notes
    is still pending).

    Issues one `.in_()` request per `_HASH_CHUNK_SIZE`-sized slice of
    `hashes` rather than one request for the whole list -- see the module
    docstring's "Chunking..." section for why a single request doesn't
    scale to a real scrape's volume.
    """

    hash_list = list(hashes)
    if not hash_list:
        return set()

    existing: set[str] = set()
    for start in range(0, len(hash_list), _HASH_CHUNK_SIZE):
        chunk = hash_list[start : start + _HASH_CHUNK_SIZE]
        result = await client.table("jobs").select("dedup_hash").in_("dedup_hash", chunk).execute()
        rows = result.data if isinstance(result.data, list) else []
        existing.update(
            row["dedup_hash"] for row in rows if isinstance(row, dict) and "dedup_hash" in row
        )

    return existing


async def dedupe_against_existing(jobs: list[NormalizedJob], client: Any) -> list[NormalizedJob]:
    """Full pipeline: in-batch dedup, then drop anything already in `jobs`
    from a previous scrape run. See the module docstring for why an
    existing DB row always wins over a freshly-scraped duplicate.
    """

    deduped = dedupe_batch(jobs)
    pairs = _hash_pairs(deduped)
    existing = await fetch_existing_dedup_hashes(client, (h for h, _ in pairs))
    return [job for dedup_hash, job in pairs if dedup_hash not in existing]
