"""FastAPI application entry point.

Registers a router per pipeline stage, each independently callable, plus the
orchestration router that wraps three of them into one LangGraph agent. CORS is
enabled for the local frontend dev origins so the web app (a separate Vite process)
can call this API cross-origin.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import classification, extraction, ingestion, orchestration, triage
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="CTI/ICS Triage Tool",
    version="0.1.0",
    description=(
        "Agent-assisted CTI triage for OT/ICS threat reports. Ingestion (PDF/HTML/URL "
        "-> plain text), extraction (IOCs + entities with source-sentence provenance), "
        "classification (ATT&CK-for-ICS technique matching via embedding retrieval + "
        "cross-encoder reranking), triage (a fully-traceable severity cascade, with a "
        "clarification-request branch instead of guessing), and orchestration (a "
        "LangGraph agent wrapping extraction/classification/triage, with real "
        "conditional edges and a trace log)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(extraction.router)
app.include_router(classification.router)
app.include_router(triage.router)
app.include_router(orchestration.router)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
