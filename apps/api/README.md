# Kortex API

FastAPI backend for Kortex — a semi-automated internship and job hunting platform.

> **Scaffolding only.** This commit sets up the project structure and a single
> `GET /health` route. Auth, jobs, applications, and worker logic land in later
> commits.

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

This starts the API on [http://localhost:8000](http://localhost:8000) and a
Redis instance on port 6379.

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## Heads up: env vars are required

The Supabase project is **not yet provisioned** (see Commit 2). All Supabase
and database settings in `app/core/config.py` are required and have no
defaults. Until real credentials exist in `.env`, any code path that reads
settings will fail at startup — this is expected. The app module imports
cleanly and the `/health` route works without them.
