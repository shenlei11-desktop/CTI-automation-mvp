"""``POST /advisory`` -- the full agent pipeline: extraction -> classification -> triage.

Wraps the three standalone stages in one LangGraph agent, with the extraction and
triage stages' review/clarification signals wired up as real conditional edges, and
every step recorded in the returned ``trace``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.orchestration import report
from app.orchestration.graph import get_graph
from app.orchestration.state import AdvisoryState
from app.schemas.orchestration import AdvisoryRequest, AdvisoryResponse

router = APIRouter(tags=["orchestration"])


@router.post("/advisory", response_model=AdvisoryResponse, summary="Run the full advisory pipeline")
def advisory(request: AdvisoryRequest) -> AdvisoryResponse:
    raw_result = get_graph().invoke(
        AdvisoryState(report_id=request.report_id, text=request.text)
    )
    final_state = AdvisoryState.model_validate(raw_result)

    return AdvisoryResponse(
        report_id=final_state.report_id,
        status=final_state.status,
        extraction=final_state.extraction,
        classification=final_state.classification,
        triage=final_state.triage,
        trace=final_state.trace,
        report=report.render(final_state),
    )
