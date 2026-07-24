"""FastAPI application entry point.

Day 1 exposes a health check and a single extraction endpoint. Later stages
(classification, triage, LangGraph orchestration) will register their own routers here.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import extraction
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="CTI/ICS Triage Tool",
    version="0.1.0",
    description=(
        "Agent-assisted CTI triage for OT/ICS threat reports. "
        "Day 1: extraction only (IOCs + entities with source-sentence provenance)."
    ),
)

app.include_router(extraction.router)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
