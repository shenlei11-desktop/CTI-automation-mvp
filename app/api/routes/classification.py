"""``POST /classify`` — maps attacker-behaviour text to ATT&CK-for-ICS techniques.

Takes explicit behaviour text(s) and returns ranked technique matches per behaviour,
with a confidence-based flag_for_review/proceed decision. Callers decide what counts
as a behaviour to classify; orchestration's automatic whole-report chunking
(`service.classify_text`) is an internal detail, not exposed here.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.classification import service
from app.schemas.classification import ClassifyRequest, ClassifyResponse

router = APIRouter(tags=["classification"])


@router.post("/classify", response_model=ClassifyResponse, summary="Classify attacker behaviours")
def classify(request: ClassifyRequest) -> ClassifyResponse:
    return service.classify(
        behaviors=request.behaviors, report_id=request.report_id, top_k=request.top_k
    )
