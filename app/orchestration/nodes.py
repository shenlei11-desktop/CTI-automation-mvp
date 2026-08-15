"""Graph nodes: each takes the current :class:`AdvisoryState` and returns a partial
update dict, following LangGraph's node contract. ``trace`` updates are always a
single-item list -- the state's ``operator.add`` reducer appends it, never replaces it.
"""

from __future__ import annotations

from app.classification import service as classification_service
from app.extraction import service as extraction_service
from app.orchestration.state import AdvisoryState
from app.schemas.orchestration import TraceEntry
from app.triage import service as triage_service


def extraction_node(state: AdvisoryState) -> dict:
    result = extraction_service.extract(state.text, report_id=state.report_id)
    entry = TraceEntry(
        node="extraction",
        detail=(
            f"Extracted {result.quality.n_iocs} IOC(s) and {result.quality.n_entities} "
            f"entity(ies); recommendation: {result.quality.recommendation}."
        ),
    )
    return {"extraction": result, "trace": [entry]}


def classification_node(state: AdvisoryState) -> dict:
    result = classification_service.classify_text(state.text, report_id=state.report_id)
    entry = TraceEntry(
        node="classification",
        detail=f"Classified {len(result.behaviors)} behaviour(s) into ATT&CK-for-ICS techniques.",
    )
    return {"classification": result, "trace": [entry]}


def triage_node(state: AdvisoryState) -> dict:
    result = triage_service.triage(state.text, report_id=state.report_id)
    entry = TraceEntry(
        node="triage",
        detail=(
            f"Scored {len(result.findings)} finding(s); decision: {result.quality.decision}."
        ),
    )
    return {"triage": result, "trace": [entry]}


def finalize_node(state: AdvisoryState) -> dict:
    entry = TraceEntry(node="finalize", detail="Pipeline completed; advisory ready.")
    return {"status": "completed", "trace": [entry]}


def needs_extraction_review_node(state: AdvisoryState) -> dict:
    entry = TraceEntry(
        node="needs_extraction_review",
        detail=(
            "Stopped after extraction: "
            f"{state.extraction.quality.reason if state.extraction else 'no extraction result.'} "
            "Classification and triage were not run."
        ),
    )
    return {"status": "needs_extraction_review", "trace": [entry]}


def needs_clarification_node(state: AdvisoryState) -> dict:
    entry = TraceEntry(
        node="needs_clarification",
        detail=(
            "Triage needs analyst input: "
            f"{state.triage.quality.reason if state.triage else 'no triage result.'} "
            "A provisional score is still attached below."
        ),
    )
    return {"status": "needs_clarification", "trace": [entry]}
