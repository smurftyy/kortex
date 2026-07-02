"""Application configuration.

Settings are loaded from environment variables (or an ``.env`` file) via
pydantic-settings. Every field except ``REDIS_URL`` is required and has no
default — the app will fail to start until real values are provided. That is
intentional: missing secrets should surface loudly rather than silently fall
back to placeholders.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str

    # Postgres (Supabase connection string)
    DATABASE_URL: str

    # Redis / ARQ queue
    REDIS_URL: str = "redis://localhost:6379"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Reading the environment is deferred until first access so that importing
    the module (e.g. in tests or tooling) does not require the environment to
    be fully configured.
    """

    return Settings()
