"""FastAPI application entry point.

Registers a router per pipeline stage, each independently callable. LangGraph
orchestration will register its own router here the same way once built.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import classification, extraction, triage
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="CTI/ICS Triage Tool",
    version="0.1.0",
    description=(
        "Agent-assisted CTI triage for OT/ICS threat reports. Extraction (IOCs + "
        "entities with source-sentence provenance), classification (ATT&CK-for-ICS "
        "technique matching via embedding retrieval + cross-encoder reranking), and "
        "triage (a fully-traceable severity cascade, with a clarification-request "
        "branch instead of guessing)."
    ),
)

app.include_router(extraction.router)
app.include_router(classification.router)
app.include_router(triage.router)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
