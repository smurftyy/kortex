# Kortex API

FastAPI backend for Kortex — a semi-automated internship and job hunting platform.

> **Scaffolding only.** This commit sets up the project structure and a single
> `GET /health` route. Auth, jobs, and applications land in later commits.

## Setup

Requires Python 3.11+.

```bash
# from apps/api/
python -m venv .venv
source .venv/bin/activate

# install the package + dev tooling
pip install -e ".[dev]"
```

Then copy the example environment file and fill in real values:

```bash
cp .env.example .env
```

## Running

With Docker Compose (from the repo root):

```bash
docker-compose up
```

This starts the API on [http://localhost:8000](http://localhost:8000), a
Redis instance on port 6379, and the ARQ worker (see [Worker](#worker) below)
— all three as separate services in the same Compose network.

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok","redis":"ok"}
```

`redis` reflects live connectivity, not just that the setting is configured
— it comes back `"unreachable"` if Redis is down, or `"unknown"` if env vars
aren't configured at all (this route still works with zero env vars set;
see [Heads up](#heads-up-env-vars-are-required) below).

## Worker

Background jobs run on [ARQ](https://arq-docs.helpmanual.io/), backed by
Redis. `app/worker.py` is scaffolding only right now — one no-op `ping` task
that proves enqueue → pickup → completion works, no real task logic yet (the
scraper worker lands in a later commit once Phase 2 scrapers exist).

Docker Compose now runs it as its own `worker` service alongside `api` and
`redis` (closing out the "no worker service yet" placeholder from the
original scaffold) — `docker-compose up` starts all three together, nothing
extra to run.

To run it locally outside Docker (from `apps/api/`, with `.env` set up and a
reachable Redis at `REDIS_URL`):

```bash
arq app.worker.WorkerSettings
```

To confirm it's actually processing jobs, enqueue one from a Python shell
(or see `tests/test_worker.py` for the same thing as an automated test):

```python
import asyncio
from arq.connections import RedisSettings, create_pool

async def main():
    pool = await create_pool(RedisSettings.from_dsn("redis://localhost:6379"))
    job = await pool.enqueue_job("ping")
    print(await job.result(timeout=5))  # "pong"

asyncio.run(main())
```

## Database

Schema changes are managed as SQL migrations under
[`supabase/migrations`](supabase/migrations), following the Supabase CLI naming
convention (`<timestamp>_description.sql`). Each migration creates its table and
its Row Level Security policies in one file.

Local CLI config lives in [`supabase/config.toml`](supabase/config.toml) with a
placeholder `project_id`.

To apply migrations to a Supabase project, link the project once, then push:

```bash
# from apps/api/
supabase link --project-ref <ref>   # one-time, uses your real project ref
supabase db push                    # applies pending migrations in supabase/migrations
```

`supabase db push` applies every migration that hasn't yet run on the linked
remote, in timestamp order.

## Heads up: env vars are required

The Supabase project is **not yet provisioned** (see Commit 2). All Supabase
and database settings in `app/core/config.py` are required and have no
defaults. Until real credentials exist in `.env`, any code path that reads
settings will fail at startup — this is expected. The app module (`app.main`)
imports cleanly and the `/health` route works without them.

`app.worker`, on the other hand, reads settings *at import time* (ARQ's CLI
needs `WorkerSettings.redis_settings` as a plain class attribute, not
something it can call lazily) — so unlike `app.main`, just importing
`app.worker` requires the full env to be configured, `REDIS_URL` included.
