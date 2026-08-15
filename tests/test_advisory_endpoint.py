"""End-to-end tests for the /advisory endpoint (requires the full pipeline)."""

from __future__ import annotations

import pytest

from tests.conftest import PIPELINE_AVAILABLE

pytestmark = pytest.mark.skipif(
    not PIPELINE_AVAILABLE, reason="spaCy NER / fastembed models not available"
)


def test_advisory_sample_report_completes(client, sample_text):
    resp = client.post("/advisory", json={"text": sample_text, "report_id": "sample-01"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["report_id"] == "sample-01"
    assert data["status"] == "completed"
    assert data["extraction"] is not None
    assert data["classification"] is not None
    assert data["triage"] is not None
    assert [t["node"] for t in data["trace"]] == [
        "extraction",
        "classification",
        "triage",
        "finalize",
    ]
    assert data["triage"]["findings"][0]["severity"] == "Critical"
    assert "CVE-2026-2841" in data["report"]


def test_advisory_short_stub_stops_after_extraction(client):
    resp = client.post("/advisory", json={"text": "too short"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "needs_extraction_review"
    assert data["extraction"] is not None
    assert data["classification"] is None
    assert data["triage"] is None
    assert "review" in data["report"].lower()


def test_advisory_empty_text_rejected(client):
    resp = client.post("/advisory", json={"text": ""})
    assert resp.status_code == 422
