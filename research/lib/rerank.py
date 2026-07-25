"""Cross-encoder reranking — a pure-ML alternative to LLM verification (Method D).

A cross-encoder scores a (query, document) pair jointly (unlike embeddings, which score
each independently then compare vectors), which is typically more accurate for
"is this the right match" ranking. It's a much smaller, task-specific model than an LLM,
so this tests whether Method C's verification step actually needs an LLM at all, or
whether a lightweight reranker over the embedding-retrieved candidates does the job.

Runs on fastembed's ONNX cross-encoders — no torch, consistent with the rest of this
project's local-only, no-heavy-dependency stack.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastembed.rerank.cross_encoder import TextCrossEncoder

DEFAULT_RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


@dataclass
class RerankedCandidate:
    technique_id: str
    score: float


class CrossEncoderReranker:
    """Thin wrapper: rerank a list of (technique_id, text) candidates against a query."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL) -> None:
        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name)

    def rerank(
        self, query: str, candidates: list[tuple[str, str]]
    ) -> list[RerankedCandidate]:
        """Score each (technique_id, text) candidate against ``query``, best first."""
        if not candidates:
            return []
        ids = [tid for tid, _ in candidates]
        texts = [text for _, text in candidates]
        scores = list(self._model.rerank(query, texts))
        ranked = sorted(zip(ids, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        return [RerankedCandidate(technique_id=tid, score=float(s)) for tid, s in ranked]
