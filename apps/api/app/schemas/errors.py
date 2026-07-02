"""Error envelope matching API_CONTRACT_kortex.md."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


def error_body(code: str, message: str, field: str | None = None) -> dict:
    """Build the ``{"error": {...}}`` envelope used for every error response."""

    return ErrorResponse(error=ErrorDetail(code=code, message=message, field=field)).model_dump()
