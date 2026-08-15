"""Agent state for the orchestration graph.

``trace`` uses LangGraph's reducer pattern: its type is annotated with ``operator.add``
so that each node's return value is *appended* to the running list rather than
replacing it -- nodes return ``{"trace": [entry]}``, never the full list.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from pydantic import BaseModel

from app.schemas.classification import ClassifyResponse
from app.schemas.extraction import ExtractResponse
from app.schemas.orchestration import TraceEntry
from app.schemas.triage import TriageResponse

AdvisoryRunStatus = Literal[
    "running", "needs_extraction_review", "needs_clarification", "completed"
]


class AdvisoryState(BaseModel):
    report_id: str | None = None
    text: str
    extraction: ExtractResponse | None = None
    classification: ClassifyResponse | None = None
    triage: TriageResponse | None = None
    trace: Annotated[list[TraceEntry], operator.add] = []
    status: AdvisoryRunStatus = "running"
