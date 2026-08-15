"""``POST /triage`` — the interpretable severity cascade.

Takes raw report text and returns a severity assessment per CVE, with a fully
traceable rule cascade and a clarification-request decision when exposure or
asset-criticality tier can't be confidently determined from the text.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.triage import TriageRequest, TriageResponse
from app.triage import service

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse, summary="Triage a threat report")
def triage(request: TriageRequest) -> TriageResponse:
    return service.triage(text=request.text, report_id=request.report_id)
