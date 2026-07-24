"""``POST /extract`` — the single Day 1 endpoint.

Takes raw report text and returns structured IOCs + entities with provenance and a
quality summary. No classification or triage yet.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.extraction import service
from app.schemas.extraction import ExtractRequest, ExtractResponse

router = APIRouter(tags=["extraction"])


@router.post("/extract", response_model=ExtractResponse, summary="Extract IOCs and entities")
def extract(request: ExtractRequest) -> ExtractResponse:
    return service.extract(text=request.text, report_id=request.report_id)
