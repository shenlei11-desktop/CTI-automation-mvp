"""Application settings (pydantic-settings).

Values are read from environment variables (and an optional ``.env`` file). Day 1 does
not read the database, but ``database_url`` is wired now so the classification stage
(Week 1, Postgres + pgvector) can use it without re-plumbing configuration.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "cti-triage"
    database_url: str = "postgresql://cti:cti@localhost:5432/cti"
    spacy_model: str = "en_core_web_sm"
    # Local dev frontend origins (Vite dev server + `vite preview`). Local-only for
    # now -- no public deployment, so no prod origin is configured here yet.
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
