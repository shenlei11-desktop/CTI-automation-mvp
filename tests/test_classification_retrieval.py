"""Unit tests for embedding retrieval (requires fastembed models)."""

from __future__ import annotations

import pytest

from app.classification.retrieval import retrieve
from tests.conftest import FASTEMBED_AVAILABLE

pytestmark = pytest.mark.skipif(
    not FASTEMBED_AVAILABLE, reason="fastembed embedding model not available"
)


def test_retrieve_returns_requested_count():
    results = retrieve("The actor exploited an internet-facing PLC.", top_n=10)
    assert len(results) == 10


def test_retrieve_sorted_descending_by_score():
    results = retrieve("The actor exploited an internet-facing PLC.", top_n=30)
    scores = [r.retrieval_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_surfaces_relevant_technique():
    # "Internet Accessible Device" (T0883) and "Exploit Public-Facing Application"
    # (T0819) are the closest semantic match for this behaviour.
    results = retrieve(
        "The threat actor identified a PLC whose web management interface was "
        "directly reachable from the public internet and exploited it.",
        top_n=30,
    )
    technique_ids = {r.technique_id for r in results}
    assert {"T0883", "T0819"} & technique_ids


def test_retrieve_scores_are_valid_cosine_range():
    results = retrieve("A generic behaviour description.", top_n=30)
    for r in results:
        assert -1.0 <= r.retrieval_score <= 1.0
