"""Embedding retrieval — stage 1 of Method D (see research/classification_bakeoff.ipynb
for the bake-off that selected this configuration over LLM-only and hybrid-LLM methods).

Configuration is empirically validated, not a default — do not change without re-running
the eval set: `BAAI/bge-base-en-v1.5`, no query-instruction prefix (every embedding
model tested scored higher without one — a deliberate reversal of an earlier default),
and the corpus is embedded as `"<name>. <short description>"`.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

import numpy as np
from fastembed import TextEmbedding

from app.classification.corpus import get_techniques

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
# Raised from 30 -> 50 after a targeted sweep this session (the bake-off itself only
# tuned N for Method C, never D): on the bake-off's own stratified 80-example sample,
# N=50 scored MRR=0.559/R@3=0.619 vs N=30's MRR=0.533/R@3=0.606 -- a real, monotonic
# gain across every N tested (20/30/40/50), for a reranking-latency cost that scales
# roughly linearly with N (~1.6s/behaviour at N=50 vs ~1.0s/behaviour at N=30 on this
# machine). See research/classification_accuracy_v2.ipynb for the full sweep.
# NOTE: `_MIN_TOP1_MARGIN` in service.py was calibrated against N=30 and has not been
# re-derived for N=50 -- a wider candidate pool can shift which candidate lands at
# rank 2, so the margin distribution may have moved slightly. Flagged, not fixed here.
HYBRID_RETRIEVAL_N = 50


@dataclass
class RawCandidate:
    technique_id: str
    retrieval_score: float  # cosine similarity, [-1, 1]


def _l2_normalise(mat: np.ndarray) -> np.ndarray:
    return mat / np.linalg.norm(mat, axis=1, keepdims=True)


@functools.lru_cache(maxsize=1)
def get_embedder() -> TextEmbedding:
    """Lazily load the embedding model (downloads ONNX weights on first use)."""
    return TextEmbedding(model_name=EMBEDDING_MODEL)


@functools.lru_cache(maxsize=1)
def _corpus_vectors() -> tuple[tuple[str, ...], np.ndarray]:
    """Embed the technique corpus once; cached for the process lifetime."""
    techniques = get_techniques()
    texts = [f"{t.name}. {t.description}" for t in techniques]
    vecs = _l2_normalise(np.array(list(get_embedder().embed(texts))))
    return tuple(t.id for t in techniques), vecs


def retrieve(text: str, top_n: int = HYBRID_RETRIEVAL_N) -> list[RawCandidate]:
    """Rank techniques by cosine similarity to `text`, best first.

    No instruction prefix is applied to `text` — validated to score higher than the
    BGE-recommended retrieval-instruction prefix on the research eval set.
    """
    technique_ids, corpus_vecs = _corpus_vectors()
    query = np.array(list(get_embedder().embed([text])))[0]
    query = query / np.linalg.norm(query)
    similarities = corpus_vecs @ query
    order = np.argsort(-similarities)[:top_n]
    return [RawCandidate(technique_ids[i], float(similarities[i])) for i in order]
