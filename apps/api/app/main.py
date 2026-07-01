"""Kortex API — FastAPI application entrypoint.

This is scaffolding only. Feature routers (auth, jobs, applications, ...) are
registered in later commits. For now the app exposes a single health check.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(
    title="Kortex API",
    description="Semi-automated internship and job hunting platform.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}
