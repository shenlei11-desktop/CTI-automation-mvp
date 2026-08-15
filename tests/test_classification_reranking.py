"""Unit tests for cross-encoder reranking (requires fastembed models)."""

from __future__ import annotations

import pytest

from app.classification.reranking import rerank
from app.classification.retrieval import RawCandidate
from tests.conftest import FASTEMBED_AVAILABLE

pytestmark = pytest.mark.skipif(
    not FASTEMBED_AVAILABLE, reason="fastembed reranker model not available"
)


def test_rerank_empty_candidates_returns_empty():
    assert rerank("some behaviour text", []) == []


def test_rerank_preserves_candidate_count():
    candidates = [
        RawCandidate("T0883", 0.5),
        RawCandidate("T0819", 0.4),
        RawCandidate("T0842", 0.3),
    ]
    results = rerank("The actor exploited an internet-facing PLC.", candidates)
    assert len(results) == 3
    assert {r.technique_id for r in results} == {"T0883", "T0819", "T0842"}


def test_rerank_reorders_by_relevance():
    # T0819 (Exploit Public-Facing Application) should clearly out-rank an unrelated
    # candidate for a behaviour explicitly about exploiting a public-facing app.
    candidates = [
        RawCandidate("T0887", 0.1),  # Wireless Sniffing — unrelated
        RawCandidate("T0819", 0.1),  # Exploit Public-Facing Application — the answer
    ]
    results = rerank(
        "The actor exploited a vulnerability in the internet-facing web application "
        "to gain unauthorized access.",
        candidates,
    )
    assert results[0].technique_id == "T0819"


def test_rerank_scores_sorted_descending():
    candidates = [
        RawCandidate("T0883", 0.1),
        RawCandidate("T0819", 0.2),
        RawCandidate("T0842", 0.3),
    ]
    results = rerank("internet-facing device exploitation", candidates)
    scores = [r.rerank_score for r in results]
    assert scores == sorted(scores, reverse=True)
