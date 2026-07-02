"""ARQ worker scaffold.

Scaffolding only — no real task logic yet. `ping` exists purely to prove
enqueue -> pickup -> completion works end-to-end against a real Redis. The
scraper worker (Phase 2) lands in a later commit once Phase 2 scrapers
exist; do not add task logic here until that commit.

Run with: ``arq app.worker.WorkerSettings`` (see README.md).
"""

from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings


async def ping(ctx: dict[str, Any]) -> str:
    """No-op health-check task."""

    return "pong"


class WorkerSettings:
    """Entrypoint class for the ``arq`` CLI (``arq app.worker.WorkerSettings``)."""

    functions = [ping]
    redis_settings = RedisSettings.from_dsn(get_settings().REDIS_URL)
