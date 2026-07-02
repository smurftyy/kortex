"""In-memory stand-ins for the Supabase/PostgREST client used by route tests.

These don't hit a real Postgres instance. `FakeTable`'s filtering is what
stands in for Postgres RLS: since every route derives its filter value from
the caller's own JWT (never from the request body), filtering correctly
here is enough to prove a route can't cross into another user's row — the
same guarantee the real RLS policies enforce, which were validated directly
against a real Postgres instance in Commits 2 and 5.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any


class _FakeQuery:
    def __init__(
        self, table: FakeTable, mode: str, values: dict | None = None, count: str | None = None
    ) -> None:
        self._table = table
        self._mode = mode
        self._values = values
        self._count = count
        self._predicates: list[Callable[[dict], bool]] = []
        self._single = False
        self._order_col: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._offset = 0

    def eq(self, column: str, value: Any) -> _FakeQuery:
        self._predicates.append(lambda row: row.get(column) == value)
        return self

    def ilike(self, column: str, pattern: str) -> _FakeQuery:
        needle = pattern.strip("%").lower()
        self._predicates.append(lambda row: needle in (row.get(column) or "").lower())
        return self

    def contains(self, column: str, value: Any) -> _FakeQuery:
        needles = list(value)
        self._predicates.append(
            lambda row: all(v in (row.get(column) or []) for v in needles)
        )
        return self

    def gte(self, column: str, value: Any) -> _FakeQuery:
        self._predicates.append(lambda row: (row.get(column) or "") >= value)
        return self

    def lte(self, column: str, value: Any) -> _FakeQuery:
        self._predicates.append(lambda row: (row.get(column) or "") <= value)
        return self

    def order(self, column: str, *, desc: bool = False, **_kwargs: Any) -> _FakeQuery:
        self._order_col = column
        self._order_desc = desc
        return self

    def limit(self, size: int, **_kwargs: Any) -> _FakeQuery:
        self._limit = size
        return self

    def offset(self, size: int) -> _FakeQuery:
        self._offset = size
        return self

    def maybe_single(self) -> _FakeQuery:
        self._single = True
        return self

    async def execute(self) -> SimpleNamespace | None:
        matches = [row for row in self._table.rows if all(p(row) for p in self._predicates)]

        if self._mode == "update":
            for row in matches:
                row.update(self._values or {})

        total = len(matches) if self._count else None

        if self._order_col is not None:
            col = self._order_col
            matches = sorted(matches, key=lambda r: r.get(col), reverse=self._order_desc)
        if self._offset:
            matches = matches[self._offset :]
        if self._limit is not None:
            matches = matches[: self._limit]

        if self._single:
            return SimpleNamespace(data=matches[0], count=total) if matches else None
        return SimpleNamespace(data=matches, count=total)


class _FakeUpsert:
    def __init__(self, table: FakeTable, values: dict, on_conflict: str | None) -> None:
        self._table = table
        self._values = values
        self._on_conflict = on_conflict

    async def execute(self) -> SimpleNamespace:
        key = self._on_conflict
        existing = next(
            (row for row in self._table.rows if key and row.get(key) == self._values.get(key)),
            None,
        )
        if existing is not None:
            existing.update(self._values)
            row = existing
        else:
            # Simulate the DB's `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
            # (Commit 2 migration) — the app never sends this on insert, so
            # Postgres fills it in.
            row = {
                "id": str(uuid.uuid4()),
                "created_at": "2026-01-01T00:00:00+00:00",
                **self._values,
            }
            self._table.rows.append(row)
        return SimpleNamespace(data=[row])


class FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def select(self, *_columns: str, count: str | None = None) -> _FakeQuery:
        return _FakeQuery(self, mode="select", count=count)

    def update(self, values: dict) -> _FakeQuery:
        return _FakeQuery(self, mode="update", values=values)

    def upsert(self, values: dict, *, on_conflict: str | None = None) -> _FakeUpsert:
        return _FakeUpsert(self, values, on_conflict)


class _FakeBucketProxy:
    def __init__(self, storage: FakeStorage, bucket: str) -> None:
        self._storage = storage
        self._bucket = bucket

    async def upload(
        self, path: str, content: bytes, options: dict[str, str] | None = None
    ) -> dict[str, str]:
        self._storage.objects[(self._bucket, path)] = content
        return {"path": path}

    async def create_signed_url(
        self, path: str, expires_in: int, options: dict[str, Any] | None = None
    ) -> dict[str, str]:
        return {"signedURL": f"https://fake.storage/{self._bucket}/{path}?token=fake"}


class FakeStorage:
    """In-memory stand-in for `client.storage` (Supabase Storage)."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def from_(self, bucket: str) -> _FakeBucketProxy:
        return _FakeBucketProxy(self, bucket)


class FakeClient:
    """Stand-in for the Supabase client returned by `get_user_scoped_client` /
    `get_anon_client`."""

    def __init__(
        self,
        *,
        profiles: list[dict] | None = None,
        preferences: list[dict] | None = None,
        jobs: list[dict] | None = None,
        job_matches: list[dict] | None = None,
    ) -> None:
        self._tables = {
            "profiles": FakeTable(profiles if profiles is not None else []),
            "preferences": FakeTable(preferences if preferences is not None else []),
            "jobs": FakeTable(jobs if jobs is not None else []),
            "job_matches": FakeTable(job_matches if job_matches is not None else []),
        }
        self.storage = FakeStorage()

    def table(self, name: str) -> FakeTable:
        return self._tables[name]
