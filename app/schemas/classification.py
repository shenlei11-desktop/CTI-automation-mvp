"""Pydantic models for the classification stage.

Defines the public API contract for ``POST /classify``. Every technique match traces
back to the behaviour text it was matched against via that behaviour's own
:class:`~app.schemas.extraction.SourceSpan`, continuing the provenance requirement from
extraction.

Scores are raw model outputs, not calibrated probabilities: ``retrieval_score`` is a
cosine similarity in ``[-1, 1]``; ``rerank_score`` is an unbounded cross-encoder logit.
Neither should be read as "% confident" — the confidence *decision* is a separate,
threshold-based judgment in :class:`ClassificationQuality`, derived empirically (see
``app/classification/service.py``), not a normalized version of these raw scores.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.extraction import Recommendation, SourceSpan


class BehaviorInput(BaseModel):
    """One piece of attacker-behaviour text to classify."""

    text: str = Field(..., min_length=1, description="The behaviour description to classify.")
    source: SourceSpan | None = Field(
        None, description="Where this behaviour text came from, if known."
    )


class ClassifyRequest(BaseModel):
    report_id: str | None = Field(
        None, description="Optional caller-supplied identifier, echoed back in the response."
    )
    behaviors: list[BehaviorInput] = Field(..., min_length=1)
    top_k: int = Field(
        5, ge=1, le=20, description="Number of ranked matches to return per behaviour."
    )


class TechniqueMatch(BaseModel):
    """One candidate ATT&CK-for-ICS technique for a behaviour, best matches ranked first."""

    technique_id: str
    technique_name: str
    tactics: list[str]
    retrieval_score: float = Field(..., description="Cosine similarity from the retrieval stage.")
    rerank_score: float = Field(
        ..., description="Raw cross-encoder logit from the reranking stage (not a probability)."
    )


class ClassificationQuality(BaseModel):
    """Confidence assessment for one behaviour's classification.

    Thresholds are derived empirically from the Phase-1 research eval set (see
    ``app/classification/service.py`` for the derivation and its documented confidence)
    — the same "explicit named constant, honestly documented" spirit as extraction's
    quality thresholds, not a black-box calibration.
    """

    top1_score: float | None = Field(None, description="Best (rank-1) candidate's rerank_score.")
    top1_margin: float | None = Field(
        None, description="rerank_score gap between the top-1 and top-2 candidates."
    )
    recommendation: Recommendation
    reason: str = Field(..., description="Human-readable justification for the recommendation.")


class BehaviorClassification(BaseModel):
    """Classification result for one input behaviour."""

    text: str
    source: SourceSpan | None = None
    matches: list[TechniqueMatch]
    quality: ClassificationQuality


class BehaviorEvidence(BaseModel):
    """One behaviour that supports a :class:`TechniqueRollup`."""

    text: str
    source: SourceSpan | None = None


class TechniqueRollup(BaseModel):
    """One ATT&CK-for-ICS technique observed anywhere in the report, deduped across
    every behaviour whose own top-1 match is this technique (e.g. two different
    sentences both pointing at the same technique collapse into one entry here, each
    kept as ``evidence`` rather than shown as separate, seemingly-independent hits).
    """

    technique_id: str
    technique_name: str
    tactics: list[str]
    attack_url: str = Field(..., description="Canonical MITRE ATT&CK technique page.")
    best_rerank_score: float = Field(
        ..., description="Highest rerank_score among this technique's evidence."
    )
    best_margin: float | None = Field(
        None, description="top1_margin of the behaviour that produced best_rerank_score."
    )
    recommendation: Recommendation = Field(
        ..., description="Recommendation of the behaviour that produced best_rerank_score."
    )
    evidence: list[BehaviorEvidence]


class ClassifyResponse(BaseModel):
    report_id: str | None = None
    behaviors: list[BehaviorClassification]
    techniques: list[TechniqueRollup] = Field(
        default_factory=list,
        description="Report-level rollup: each technique observed, deduped, with its "
        "supporting evidence sentence(s). Derived from behaviors, not a separate call.",
    )
