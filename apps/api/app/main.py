"""Kortex API — FastAPI application entrypoint.

Feature routers are registered incrementally: `GET /auth/me` lands in
Commit 3; profile/preferences CRUD lands in Commit 4; jobs/job_matches
lands in Commit 6. Signup/login/refresh follow in a later commit.
"""

from __future__ import annotations

import redis.asyncio as redis_asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.profile import router as profile_router
from app.core.config import get_settings
from app.middleware.auth import JWTAuthMiddleware

app = FastAPI(
    title="Kortex API",
    description="Semi-automated internship and job hunting platform.",
    version="0.1.0",
)

app.add_middleware(JWTAuthMiddleware)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Serialize ``HTTPException.detail`` as the top-level response body.

    Routes raise ``HTTPException`` with ``detail={"error": {...}}`` matching
    API_CONTRACT_kortex.md's error envelope; without this handler FastAPI
    would nest that dict under an extra ``"detail"`` key.
    """

    return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe.

    Also reports Redis reachability — not just API liveness — so a worker
    that can't reach Redis (Commit 9) is visible here instead of failing
    silently. Redis being down does not fail this endpoint's own 200: most
    routes don't depend on it yet, so a transient Redis blip shouldn't look
    like the API itself is unhealthy to an orchestrator's liveness probe.

    Settings are read defensively (not via the usual fail-loudly
    ``get_settings()`` contract): this route has always worked with zero
    env vars configured (see README.md), and that guarantee still holds —
    an unconfigured environment reports ``redis: "unknown"`` rather than
    500ing the whole liveness check.
    """

    try:
        redis_url = get_settings().REDIS_URL
    except Exception:
        return {"status": "ok", "redis": "unknown"}

    redis_status = "ok"
    client = redis_asyncio.Redis.from_url(redis_url)
    try:
        await client.ping()
    except Exception:
        redis_status = "unreachable"
    finally:
        await client.aclose()

    return {"status": "ok", "redis": redis_status}
