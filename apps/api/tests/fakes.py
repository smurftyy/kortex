"""In-memory stand-ins for the Supabase/PostgREST client used by route tests.

These don't hit a real Postgres instance. `FakeTable`'s `.eq(...)` filtering
is what stands in for Postgres RLS: since every route derives its filter
value from the caller's own JWT (never from the request body), filtering
correctly here is enough to prove a route can't cross into another user's
row — the same guarantee the real `profiles`/`preferences` RLS policies
enforce, which were validated directly against a real Postgres instance in
Commit 2.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any


class _FakeQuery:
    def __init__(self, table: FakeTable, mode: str, values: dict | None = None) -> None:
        self._table = table
        self._mode = mode
        self._values = values
        self._filters: dict[str, Any] = {}
        self._single = False

    def eq(self, column: str, value: Any) -> _FakeQuery:
        self._filters[column] = value
        return self

    def maybe_single(self) -> _FakeQuery:
        self._single = True
        return self

    async def execute(self) -> SimpleNamespace | None:
        matches = [
            row
            for row in self._table.rows
            if all(row.get(k) == v for k, v in self._filters.items())
        ]

        if self._mode == "update":
            for row in matches:
                row.update(self._values or {})

        if self._single:
            return SimpleNamespace(data=matches[0]) if matches else None
        return SimpleNamespace(data=matches)


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
            row = {"id": str(uuid.uuid4()), **self._values}
            self._table.rows.append(row)
        return SimpleNamespace(data=[row])


class FakeTable:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def select(self, *_columns: str) -> _FakeQuery:
        return _FakeQuery(self, mode="select")

    def update(self, values: dict) -> _FakeQuery:
        return _FakeQuery(self, mode="update", values=values)

    def upsert(self, values: dict, *, on_conflict: str | None = None) -> _FakeUpsert:
        return _FakeUpsert(self, values, on_conflict)


class FakeClient:
    """Stand-in for the RLS-scoped Supabase client returned by
    `get_user_scoped_client`."""

    def __init__(
        self, *, profiles: list[dict] | None = None, preferences: list[dict] | None = None
    ) -> None:
        self._tables = {
            "profiles": FakeTable(profiles if profiles is not None else []),
            "preferences": FakeTable(preferences if preferences is not None else []),
        }

    def table(self, name: str) -> FakeTable:
        return self._tables[name]
