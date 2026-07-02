"""Per-request Supabase client helpers."""

from __future__ import annotations

from supabase import acreate_client
from supabase._async.client import AsyncClient

from app.core.config import get_settings


async def get_user_scoped_client(access_token: str) -> AsyncClient:
    """Build a Supabase client scoped to the caller's own access token.

    The client is created with the anon key (so the API gateway accepts the
    request), then its PostgREST Authorization header is swapped to the
    caller's own JWT. Postgres RLS evaluates ``auth.uid()`` against that
    token, so the ownership policies from Commit 2 are what actually scope
    the query — the service role key is never used on this path.
    """

    settings = get_settings()
    client = await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.postgrest.auth(access_token)
    return client
