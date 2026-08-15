"""Classification service: orchestrates Method D (retrieve then rerank) and computes
a confidence decision.

This is the single entry point the API calls. It runs retrieval + reranking for each
input behaviour and composes the results into Pydantic response models, attaching a
per-behaviour :class:`ClassificationQuality` decision.

Confidence threshold note: unlike ``app/extraction/service.py``'s thresholds (which are
sensible-but-undedrived defaults), ``_MIN_TOP1_MARGIN`` below was *derived* from a
Youden's-J search over 259 real labeled examples — see
``research/classification_confidence_calibration.ipynb`` for the analysis. It uses only
the self-relative top1-vs-top2 score margin, not the absolute rerank score: the
calibration run found the absolute score barely separates correct from incorrect
predictions (correct-group p25 and incorrect-group p50 landed on nearly the same
value), while the margin does (median 2.35 for correct vs. 0.77 for incorrect). This is
still not a rigorously cross-validated cutoff -- 259 examples over 79 classes with a
general-purpose reranker is not enough data for that -- so read it as "catches many
genuinely-wrong predictions, avoids flagging most genuinely-right ones," not a
calibrated probability boundary.
"""

from __future__ import annotations

from app.classification import reranking, retrieval, segmentation
from app.classification.corpus import get_technique_by_id
from app.schemas.classification import (
    BehaviorClassification,
    BehaviorEvidence,
    BehaviorInput,
    ClassificationQuality,
    ClassifyResponse,
    TechniqueMatch,
    TechniqueRollup,
)
from app.schemas.extraction import SourceSpan

# Derived empirically (Youden's J = 0.395 at this point, vs. peak J = 0.405 at 1.70) --
# chosen slightly below the exact optimum to reduce needlessly flagging correct
# predictions (FPR 27% vs 36% at the peak) while still catching most wrong ones
# (TPR 67% vs 76%). See the calibration notebook for the full derivation.
_MIN_TOP1_MARGIN = 1.25

_ATTACK_URL_TEMPLATE = "https://attack.mitre.org/techniques/{technique_id}"

# Internal chunking knobs for classify_text() (orchestration's entry point only).
# This heuristic was never validated by the bake-off, which worked on pre-curated
# behaviour snippets, not whole multi-paragraph reports -- documented, not proven.
_MIN_BEHAVIOR_SENTENCE_LENGTH = 40
_MAX_BEHAVIORS_PER_REPORT = 20


def _assess_confidence(ranked: list[reranking.RawRerankedCandidate]) -> ClassificationQuality:
    if not ranked:
        return ClassificationQuality(
            top1_score=None,
            top1_margin=None,
            recommendation="flag_for_review",
            reason="No candidate techniques were retrieved for this behaviour.",
        )

    top1_score = ranked[0].rerank_score
    margin = (ranked[0].rerank_score - ranked[1].rerank_score) if len(ranked) > 1 else None

    if margin is not None and margin < _MIN_TOP1_MARGIN:
        recommendation = "flag_for_review"
        reason = (
            f"Top two candidates are too close to confidently discriminate "
            f"(margin {margin:.2f} < {_MIN_TOP1_MARGIN}); needs analyst judgement."
        )
    else:
        recommendation = "proceed"
        reason = (
            f"Top match scored {top1_score:.2f}"
            + (f", {margin:.2f} clear of the runner-up." if margin is not None else ".")
        )

    return ClassificationQuality(
        top1_score=top1_score, top1_margin=margin, recommendation=recommendation, reason=reason
    )


def _classify_one(behavior: BehaviorInput, top_k: int) -> BehaviorClassification:
    technique_by_id = get_technique_by_id()
    candidates = retrieval.retrieve(behavior.text)
    ranked = reranking.rerank(behavior.text, candidates)

    # Confidence is computed from the FULL reranked list's rank-1/rank-2, not the
    # top_k slice -- truncating first would silently change the decision.
    quality = _assess_confidence(ranked)

    retrieval_score_by_id = {c.technique_id: c.retrieval_score for c in candidates}
    matches = [
        TechniqueMatch(
            technique_id=r.technique_id,
            technique_name=technique_by_id[r.technique_id].name,
            tactics=technique_by_id[r.technique_id].tactics,
            retrieval_score=retrieval_score_by_id[r.technique_id],
            rerank_score=r.rerank_score,
        )
        for r in ranked[:top_k]
    ]

    return BehaviorClassification(
        text=behavior.text, source=behavior.source, matches=matches, quality=quality
    )


def _build_rollup(results: list[BehaviorClassification]) -> list[TechniqueRollup]:
    """Aggregate each behaviour's OWN top-1 match into one entry per technique --
    dedups repeats (two different sentences both landing on the same technique) and
    keeps every supporting behaviour as evidence rather than as separate, seemingly
    independent hits.
    """
    best: dict[str, tuple[BehaviorClassification, TechniqueMatch]] = {}
    evidence: dict[str, list[BehaviorEvidence]] = {}

    for behavior in results:
        if not behavior.matches:
            continue
        top = behavior.matches[0]
        evidence.setdefault(top.technique_id, []).append(
            BehaviorEvidence(text=behavior.text, source=behavior.source)
        )
        current_best = best.get(top.technique_id)
        if current_best is None or top.rerank_score > current_best[1].rerank_score:
            best[top.technique_id] = (behavior, top)

    rollups = [
        TechniqueRollup(
            technique_id=technique_id,
            technique_name=match.technique_name,
            tactics=match.tactics,
            attack_url=_ATTACK_URL_TEMPLATE.format(technique_id=technique_id),
            best_rerank_score=match.rerank_score,
            best_margin=behavior.quality.top1_margin,
            recommendation=behavior.quality.recommendation,
            evidence=evidence[technique_id],
        )
        for technique_id, (behavior, match) in best.items()
    ]
    rollups.sort(key=lambda r: r.best_rerank_score, reverse=True)
    return rollups


def classify(
    behaviors: list[BehaviorInput], report_id: str | None = None, top_k: int = 5
) -> ClassifyResponse:
    """Classify each supplied behaviour independently. The explicit public contract:
    the caller decides what counts as a behaviour to classify."""
    results = [_classify_one(b, top_k) for b in behaviors]
    return ClassifyResponse(
        report_id=report_id, behaviors=results, techniques=_build_rollup(results)
    )


def classify_text(text: str, report_id: str | None = None, top_k: int = 5) -> ClassifyResponse:
    """Internal convenience wrapper for orchestration only -- NOT exposed via HTTP.

    Segments ``text`` into sentence-level behaviours via ``segmentation.segment()``
    (headers, non-behaviour sections, and negated "not affected" claims already
    filtered out there), drops anything still under ``_MIN_BEHAVIOR_SENTENCE_LENGTH``,
    and caps the count at ``_MAX_BEHAVIORS_PER_REPORT`` to bound latency. The caller of
    ``classify()`` should prefer supplying curated behaviours directly when possible.
    """
    behaviors = [
        BehaviorInput(
            text=seg.text, source=SourceSpan(sentence=seg.text, start=seg.start, end=seg.end)
        )
        for seg in segmentation.segment(text)
        if len(seg.text.strip()) >= _MIN_BEHAVIOR_SENTENCE_LENGTH
    ][:_MAX_BEHAVIORS_PER_REPORT]

    if not behaviors:
        return ClassifyResponse(report_id=report_id, behaviors=[])

    return classify(behaviors, report_id=report_id, top_k=top_k)
