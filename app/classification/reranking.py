"""Cross-encoder reranking — stage 2 of Method D.

Reranks the candidates `retrieval.py` surfaces, using a small dedicated cross-encoder
instead of an LLM — deterministic and architecturally incapable of hallucinating an ID,
since it only ever reorders candidates it was given.

Scores are raw, unbounded cross-encoder logits — NOT calibrated probabilities. No
sigmoid/softmax is applied anywhere in this pipeline (matches the validated research
configuration exactly); callers must not treat `rerank_score` as a 0-1 confidence.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

from fastembed.rerank.cross_encoder import TextCrossEncoder

from app.classification.corpus import get_technique_by_id
from app.classification.retrieval import RawCandidate

RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


@dataclass
class RawRerankedCandidate:
    technique_id: str
    rerank_score: float  # raw cross-encoder logit — unbounded, not a probability


@functools.lru_cache(maxsize=1)
def get_reranker() -> TextCrossEncoder:
    """Lazily load the reranker model (downloads ONNX weights on first use)."""
    return TextCrossEncoder(model_name=RERANKER_MODEL)


def rerank(text: str, candidates: list[RawCandidate]) -> list[RawRerankedCandidate]:
    """Re-score `candidates` against `text`, best first.

    Candidate text uses the FULL (untruncated) technique description — deliberately
    richer than retrieval's short-description corpus text, matching the validated
    research configuration.
    """
    if not candidates:
        return []
    technique_by_id = get_technique_by_id()
    ids = [c.technique_id for c in candidates]
    texts = [
        f"{technique_by_id[tid].name}. {technique_by_id[tid].description_full}" for tid in ids
    ]
    scores = list(get_reranker().rerank(text, texts))
    ranked = sorted(zip(ids, scores, strict=True), key=lambda pair: pair[1], reverse=True)
    return [RawRerankedCandidate(tid, float(score)) for tid, score in ranked]
