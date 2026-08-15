"""Tests for the orchestration graph, invoked directly (no HTTP).

Needs the full pipeline (spaCy NER model for extraction, fastembed models for
classification) since every path runs extraction at minimum, and the completed /
needs_clarification paths also run classification.
"""

from __future__ import annotations

import pytest

from app.orchestration.graph import get_graph
from app.orchestration.state import AdvisoryState
from tests.conftest import PIPELINE_AVAILABLE

pytestmark = pytest.mark.skipif(
    not PIPELINE_AVAILABLE, reason="spaCy NER / fastembed models not available"
)


def _run(text: str, report_id: str | None = None) -> AdvisoryState:
    raw = get_graph().invoke(AdvisoryState(report_id=report_id, text=text))
    return AdvisoryState.model_validate(raw)


def test_completed_path_runs_all_stages(sample_text):
    final = _run(sample_text, report_id="sample-01")
    assert final.status == "completed"
    assert [t.node for t in final.trace] == ["extraction", "classification", "triage", "finalize"]
    assert final.extraction is not None
    assert final.classification is not None
    assert final.triage is not None
    assert final.triage.findings[0].severity == "Critical"


def test_needs_extraction_review_is_a_hard_stop():
    # Well below extraction's minimum-text-length threshold.
    final = _run("too short")
    assert final.status == "needs_extraction_review"
    assert [t.node for t in final.trace] == ["extraction", "needs_extraction_review"]
    assert final.extraction is not None
    # The hard stop: classification and triage never ran at all.
    assert final.classification is None
    assert final.triage is None


def test_needs_clarification_still_attaches_a_provisional_score():
    text = (
        "A vulnerability tracked as CVE-2026-9999 has a CVSS v3.1 base score of 8.1. "
        "Organizations should apply the vendor patch as soon as possible. This advisory "
        "provides general guidance for affected deployments without further detail about "
        "the environment or the specific device roles involved, since no additional "
        "context was available at the time of writing this report to any recipients."
    )
    final = _run(text)
    assert final.status == "needs_clarification"
    assert [t.node for t in final.trace] == [
        "extraction",
        "classification",
        "triage",
        "needs_clarification",
    ]
    assert final.triage is not None
    assert final.triage.findings[0].severity is not None
