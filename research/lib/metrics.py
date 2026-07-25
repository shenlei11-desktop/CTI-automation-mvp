"""Shared evaluation metrics for the classification bake-off.

Defined once and imported by every method so the comparison can't drift: if the same
formula were copy-pasted into several notebook cells, a subtle inconsistency between
copies would silently invalidate the whole comparison.

Two metric families live here:

**Rank-based (primary)** — :func:`reciprocal_rank`, :func:`average_precision`,
:func:`recall_at_k`, aggregated by :func:`rank_score_method` into :class:`RankMetrics`
(MRR, MAP, Recall@k for several k). These score a method's full *ranking* with no
forced prediction count, so they are fair across methods that naturally emit different
numbers of predictions (an LLM asked for "up to 5" vs. a reranker that ranks every
retrieved candidate) — and they match the real task, which is producing a ranked
shortlist for a human analyst, not a fixed-size guess.

**Set-based (secondary, at a fixed operating point)** — :func:`score_report` /
:func:`score_method`, using a fixed ``top_k`` cutoff. Kept for an "if you only look at
the top-k" view, but note this is more sensitive to ``top_k`` matching the true label
count. If a report has 1 true label, forcing ``top_k=3`` predictions caps precision at
1/3 even for a perfect ranker — that ceiling effect should be kept in mind when reading
precision/F1 numbers, which is why the rank-based metrics above are primary.

Both families score a single, shared unit: a :class:`MethodResult` — one method's
*ranked* list of predicted technique IDs for one report, versus the true IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MethodResult:
    """One method's prediction for one report."""

    report_id: str
    true_ids: list[str]
    ranked_ids: list[str]  # predicted technique IDs, best first
    parse_failure: bool = False  # LLM output could not be parsed (LLM methods only)
    hallucinated_id_count: int = 0  # predicted IDs that are not real techniques


@dataclass
class PerReportScore:
    report_id: str
    precision: float
    recall: float
    f1: float
    top1_hit: bool
    top3_hit: bool
    predicted: list[str]
    true: list[str]


@dataclass
class MethodScore:
    """Macro-averaged scores for a whole method, for the comparison table."""

    method: str
    precision: float
    recall: float
    f1: float
    top1_hit_rate: float
    top3_hit_rate: float
    parse_failure_rate: float
    hallucinated_id_total: int
    n_reports: int
    per_report: list[PerReportScore] = field(default_factory=list)


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_report(result: MethodResult, top_k: int) -> PerReportScore:
    true_set = set(result.true_ids)
    predicted = result.ranked_ids[:top_k]
    predicted_set = set(predicted)

    hits = predicted_set & true_set
    precision = len(hits) / len(predicted_set) if predicted_set else 0.0
    recall = len(hits) / len(true_set) if true_set else 0.0

    return PerReportScore(
        report_id=result.report_id,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        top1_hit=bool(result.ranked_ids) and result.ranked_ids[0] in true_set,
        top3_hit=bool(true_set & set(result.ranked_ids[:3])),
        predicted=predicted,
        true=result.true_ids,
    )


def recall_at_n(results: list[MethodResult], n: int) -> float:
    """Fraction of true technique IDs present anywhere in the first ``n`` ranked IDs.

    Used to separate a retrieval problem from a verification problem: if recall@N is
    already low at a generous N, no verifier can recover the missing labels — the fix
    belongs in retrieval (embedding model, N) not in the LLM prompt.
    """
    per_report = []
    for r in results:
        true_set = set(r.true_ids)
        if not true_set:
            continue
        hits = true_set & set(r.ranked_ids[:n])
        per_report.append(len(hits) / len(true_set))
    return sum(per_report) / len(per_report) if per_report else 0.0


def reciprocal_rank(true_ids: list[str], ranked_ids: list[str]) -> float:
    """1/rank (1-indexed) of the first true ID found in ``ranked_ids``; 0.0 if none.

    The standard multi-label extension of MRR: with several true IDs per report, only
    the rank of the *first* one found matters for this metric (MAP below credits the
    rest). 0.0 both when nothing is found and when ``true_ids`` is empty.
    """
    true_set = set(true_ids)
    for i, tid in enumerate(ranked_ids, start=1):
        if tid in true_set:
            return 1.0 / i
    return 0.0


def average_precision(true_ids: list[str], ranked_ids: list[str]) -> float:
    """Standard multi-label average precision.

    Precision is computed at each rank where a true ID appears, then averaged and
    normalized by the *total* number of true IDs — not just the ones actually found —
    so a true ID the method never surfaces at all still costs AP, exactly as it should.
    """
    true_set = set(true_ids)
    if not true_set:
        return 0.0
    hits = 0
    precisions_at_hit = []
    for i, tid in enumerate(ranked_ids, start=1):
        if tid in true_set:
            hits += 1
            precisions_at_hit.append(hits / i)
    return sum(precisions_at_hit) / len(true_set)


def recall_at_k(true_ids: list[str], ranked_ids: list[str], k: int) -> float:
    """Fraction of ``true_ids`` present in the first ``k`` of ``ranked_ids`` — one report."""
    true_set = set(true_ids)
    if not true_set:
        return 0.0
    hits = true_set & set(ranked_ids[:k])
    return len(hits) / len(true_set)


@dataclass
class RankMetrics:
    """Rank-based scores for a whole method — the primary comparison metrics."""

    method: str
    mrr: float
    map: float
    recall_at_k: dict[int, float]  # e.g. {1: 0.40, 3: 0.62, 5: 0.71}
    n_reports: int


def rank_score_method(
    method: str, results: list[MethodResult], ks: tuple[int, ...] = (1, 3, 5)
) -> RankMetrics:
    """Aggregate MRR / MAP / Recall@k across all reports for one method."""
    if not results:
        raise ValueError(f"No results to score for method {method!r}")
    n = len(results)
    mrr = sum(reciprocal_rank(r.true_ids, r.ranked_ids) for r in results) / n
    map_score = sum(average_precision(r.true_ids, r.ranked_ids) for r in results) / n
    recalls = {k: sum(recall_at_k(r.true_ids, r.ranked_ids, k) for r in results) / n for k in ks}
    return RankMetrics(method=method, mrr=mrr, map=map_score, recall_at_k=recalls, n_reports=n)


def score_method(method: str, results: list[MethodResult], top_k: int) -> MethodScore:
    """Macro-average a method's per-report scores into one :class:`MethodScore`."""
    if not results:
        raise ValueError(f"No results to score for method {method!r}")

    per_report = [score_report(r, top_k) for r in results]
    n = len(per_report)

    def mean(values: list[float]) -> float:
        return sum(values) / n

    return MethodScore(
        method=method,
        precision=mean([s.precision for s in per_report]),
        recall=mean([s.recall for s in per_report]),
        f1=mean([s.f1 for s in per_report]),
        top1_hit_rate=mean([1.0 if s.top1_hit else 0.0 for s in per_report]),
        top3_hit_rate=mean([1.0 if s.top3_hit else 0.0 for s in per_report]),
        parse_failure_rate=mean([1.0 if r.parse_failure else 0.0 for r in results]),
        hallucinated_id_total=sum(r.hallucinated_id_count for r in results),
        n_reports=n,
        per_report=per_report,
    )
