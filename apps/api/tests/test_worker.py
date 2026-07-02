"""Live-Redis test for the ARQ worker scaffold.

`app.worker.WorkerSettings` resolves `REDIS_URL` at import time (ARQ's CLI
needs `redis_settings` as a plain class attribute, not something it can
call lazily), so `app.worker` is imported inside the test body — after the
`_env` fixture has set env vars — rather than at module load.

Skipped automatically if Redis isn't reachable: the rest of this project's
suite runs fully offline, and this is the one exception that genuinely
needs a real Redis, same "validate against the real thing" standard used
for the DB migrations (Commits 2, 5, 6, 7). Point `REDIS_URL` at a running
Redis (e.g. `docker run --rm -p 6379:6379 redis:7-alpine`) to exercise it.
"""

from __future__ import annotations

import os

import pytest
import redis.asyncio as redis_asyncio
from arq.connections import RedisSettings, create_pool
from arq.worker import Worker

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


async def _redis_available() -> bool:
    try:
        probe = redis_asyncio.Redis.from_url(REDIS_URL)
        await probe.ping()
        await probe.aclose()
        return True
    except Exception:
        return False


async def test_worker_enqueues_and_processes_ping_job(_env: None) -> None:
    if not await _redis_available():
        pytest.skip(f"No Redis reachable at {REDIS_URL}")

    from app.worker import ping

    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    pool = await create_pool(redis_settings)
    worker = Worker(functions=[ping], redis_settings=redis_settings, burst=True, poll_delay=0)

    try:
        job = await pool.enqueue_job("ping")
        assert job is not None

        await worker.async_run()

        result = await job.result(timeout=5)
        assert result == "pong"
    finally:
        await worker.close()
        await pool.aclose()
