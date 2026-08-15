"""Pydantic models for the orchestration stage.

Defines the public API contract for ``POST /advisory``, the LangGraph agent that wraps
extraction -> classification -> triage into one call. Both hard-stop conditions from
the earlier stages (extraction's ``flag_for_review``, triage's ``needs_clarification``)
surface here as ``status`` rather than being swallowed -- the caller always sees why a
run didn't reach ``completed``, and whatever partial results exist are still attached
(never withheld).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.classification import ClassifyResponse
from app.schemas.extraction import ExtractResponse
from app.schemas.triage import TriageResponse

AdvisoryStatus = Literal["completed", "needs_extraction_review", "needs_clarification"]


class TraceEntry(BaseModel):
    """One step of the agent's run, in the order it happened."""

    node: str = Field(..., description="Which node produced this entry, e.g. 'extraction'.")
    detail: str = Field(..., description="Human-readable summary of what happened.")


class AdvisoryRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, description="Raw report text to run the full pipeline over."
    )
    report_id: str | None = Field(
        None, description="Optional caller-supplied identifier, echoed back in the response."
    )


class AdvisoryResponse(BaseModel):
    report_id: str | None = None
    status: AdvisoryStatus
    extraction: ExtractResponse | None = None
    classification: ClassifyResponse | None = None
    triage: TriageResponse | None = None
    trace: list[TraceEntry]
    report: str = Field(..., description="Human-readable rendered advisory.")
