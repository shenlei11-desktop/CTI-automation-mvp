"""``POST /ingest``, ``POST /ingest/pdf``, and ``GET /ingest/feed`` -- turn a report
source into plain text, or list real current advisories to feed in.

Three modes share one JSON-body route (text passthrough, raw HTML, URL fetch); PDF
needs a separate multipart route since FastAPI can't mix a JSON body with a file
upload on the same route.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, UploadFile

from app.ingestion import feed, service
from app.ingestion.models import IngestionError
from app.schemas.ingestion import FeedResponse, IngestRequest, IngestResponse

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse, summary="Ingest text, HTML, or a URL")
def ingest(request: IngestRequest) -> IngestResponse:
    try:
        return service.ingest(request)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/ingest/pdf", response_model=IngestResponse, summary="Ingest an uploaded PDF")
async def ingest_pdf(file: UploadFile) -> IngestResponse:
    data = await file.read()
    try:
        return service.ingest_pdf(data)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/ingest/feed", response_model=FeedResponse, summary="List real, current CISA ICS advisories"
)
def ingest_feed(limit: int = Query(10, ge=1, le=30)) -> FeedResponse:
    try:
        items = feed.fetch_ics_advisories(limit=limit)
    except IngestionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FeedResponse(items=items)
