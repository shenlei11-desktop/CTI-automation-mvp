"""End-to-end tests for the /classify endpoint (requires fastembed models)."""

from __future__ import annotations

import pytest

from tests.conftest import FASTEMBED_AVAILABLE

pytestmark = pytest.mark.skipif(
    not FASTEMBED_AVAILABLE, reason="fastembed embedding/reranker models not available"
)


def test_classify_clear_behavior_proceeds(client):
    resp = client.post(
        "/classify",
        json={
            "report_id": "test-01",
            "behaviors": [
                {
                    "text": (
                        "The threat actor identified a PLC whose web-based management "
                        "interface was directly reachable from the public internet and "
                        "exploited an authentication bypass to gain access without valid "
                        "credentials."
                    )
                }
            ],
            "top_k": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == "test-01"
    assert len(data["behaviors"]) == 1

    behavior = data["behaviors"][0]
    assert behavior["quality"]["recommendation"] == "proceed"
    assert len(behavior["matches"]) == 3
    technique_ids = {m["technique_id"] for m in behavior["matches"]}
    assert "T0883" in technique_ids  # Internet Accessible Device

    # Matches are ranked best-first by rerank_score.
    scores = [m["rerank_score"] for m in behavior["matches"]]
    assert scores == sorted(scores, reverse=True)


def test_classify_vague_behavior_flagged_for_review(client):
    resp = client.post(
        "/classify",
        json={
            "behaviors": [
                {"text": "Something suspicious happened on the network at some point."}
            ]
        },
    )
    assert resp.status_code == 200
    behavior = resp.json()["behaviors"][0]
    assert behavior["quality"]["recommendation"] == "flag_for_review"
    assert "too close" in behavior["quality"]["reason"] or "margin" in behavior["quality"]["reason"]


def test_classify_empty_behaviors_rejected(client):
    resp = client.post("/classify", json={"behaviors": []})
    assert resp.status_code == 422


def test_classify_missing_text_rejected(client):
    resp = client.post("/classify", json={"behaviors": [{"text": ""}]})
    assert resp.status_code == 422
