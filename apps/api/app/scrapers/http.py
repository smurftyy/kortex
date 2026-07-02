"""Shared HTTP layer for scrapers: timeout, retry-with-backoff, per-source
rate limiting.

Every knob here is a constructor parameter, never a hardcoded constant —
Commits 12-14 each configure their own timeout/retry/rate-limit values per
source, since a slow/strict board needs different settings than a fast one.
"""

from __future__ import annotations

import asyncio
import logging
import time
from types import TracebackType

import httpx

logger = logging.getLogger(__name__)

# Status codes worth retrying: rate-limited or a transient server error.
# Everything else (404, 401, ...) is retried this many times only to waste
# the source's rate-limit budget for no benefit, so it's raised immediately.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RateLimiter:
    """At most one request every `min_interval_seconds`, enforced by
    delaying `acquire()` as needed.

    One instance per scraper/source: each source's configured rate limit
    is independent of every other source's, by construction.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._last_request_at: float | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._last_request_at is not None:
                wait = self._min_interval - (now - self._last_request_at)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()


class ScraperHTTPClient:
    """Thin async HTTP wrapper: timeout + retry-with-backoff + optional
    rate limiting. Use as an async context manager so one connection pool
    is reused across every request in a single scrape run.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_base_seconds: float = 1.0,
        rate_limiter: RateLimiter | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff_base = backoff_base_seconds
        self._rate_limiter = rate_limiter
        # Injectable for tests (`httpx.MockTransport`) — deterministic
        # retry-path testing without hitting a real flaky/slow endpoint.
        # None in real use, which is httpx's normal live-network transport.
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ScraperHTTPClient:
        self._client = httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        if self._client is None:
            raise RuntimeError(
                "ScraperHTTPClient must be used as `async with ScraperHTTPClient(...)`"
            )

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if self._rate_limiter is not None:
                await self._rate_limiter.acquire()

            try:
                response = await self._client.get(url, **kwargs)  # type: ignore[arg-type]
                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response
                last_exc = httpx.HTTPStatusError(
                    f"retryable status {response.status_code}",
                    request=response.request,
                    response=response,
                )
            except httpx.HTTPStatusError:
                raise  # non-retryable 4xx (e.g. 404, 401) -- fail immediately
            except httpx.TransportError as exc:
                last_exc = exc

            if attempt < self._max_retries:
                delay = self._backoff_base * (2**attempt)
                logger.warning(
                    "request to %s failed (attempt %d/%d): %s -- retrying in %.1fs",
                    url,
                    attempt + 1,
                    self._max_retries + 1,
                    last_exc,
                    delay,
                )
                await asyncio.sleep(delay)

        assert last_exc is not None
        raise last_exc
