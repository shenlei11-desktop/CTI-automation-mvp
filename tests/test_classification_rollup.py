"""Unit tests for report-level technique rollup (pure aggregation over already-built
BehaviorClassification objects -- no model calls, runs unconditionally).
"""

from __future__ import annotations

from app.classification.service import _build_rollup
from app.schemas.classification import (
    BehaviorClassification,
    ClassificationQuality,
    TechniqueMatch,
)


def _match(technique_id: str, score: float, name: str = "Some Technique") -> TechniqueMatch:
    return TechniqueMatch(
        technique_id=technique_id,
        technique_name=name,
        tactics=["initial-access"],
        retrieval_score=0.5,
        rerank_score=score,
    )


def _behavior(text: str, top_id: str, top_score: float, recommendation="proceed"):
    return BehaviorClassification(
        text=text,
        source=None,
        matches=[_match(top_id, top_score)],
        quality=ClassificationQuality(
            top1_score=top_score, top1_margin=2.0, recommendation=recommendation, reason="test"
        ),
    )


def test_duplicate_technique_across_behaviors_collapses_to_one_rollup():
    behaviors = [
        _behavior("first sentence", "T0866", -1.0),
        _behavior("second sentence", "T0866", -3.0),
    ]
    rollup = _build_rollup(behaviors)
    assert len(rollup) == 1
    assert rollup[0].technique_id == "T0866"
    assert len(rollup[0].evidence) == 2


def test_rollup_keeps_the_higher_scoring_evidence_as_best():
    behaviors = [
        _behavior("weaker match", "T0866", -3.0, recommendation="flag_for_review"),
        _behavior("stronger match", "T0866", -1.0, recommendation="proceed"),
    ]
    rollup = _build_rollup(behaviors)
    assert rollup[0].best_rerank_score == -1.0
    assert rollup[0].recommendation == "proceed"


def test_rollup_sorted_best_score_first():
    behaviors = [
        _behavior("low", "T0800", -9.0),
        _behavior("high", "T0801", 1.0),
        _behavior("mid", "T0802", -2.0),
    ]
    rollup = _build_rollup(behaviors)
    assert [r.technique_id for r in rollup] == ["T0801", "T0802", "T0800"]


def test_rollup_includes_attack_url():
    rollup = _build_rollup([_behavior("text", "T0883", 0.5)])
    assert rollup[0].attack_url == "https://attack.mitre.org/techniques/T0883"


def test_behaviors_with_no_matches_are_excluded_from_rollup():
    empty = BehaviorClassification(
        text="no matches",
        source=None,
        matches=[],
        quality=ClassificationQuality(
            top1_score=None, top1_margin=None, recommendation="flag_for_review", reason="none"
        ),
    )
    rollup = _build_rollup([empty])
    assert rollup == []


def test_empty_behavior_list_returns_empty_rollup():
    assert _build_rollup([]) == []
