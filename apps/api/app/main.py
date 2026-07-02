"""Kortex API — FastAPI application entrypoint.

Feature routers are registered incrementally: `GET /auth/me` lands in
Commit 3; profile/preferences CRUD lands in Commit 4; jobs/job_matches
lands in Commit 6. Signup/login/refresh follow in a later commit.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.profile import router as profile_router
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
    """Liveness probe."""

    return {"status": "ok"}
