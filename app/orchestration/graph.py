"""The orchestration agent graph: extraction -> classification -> triage -> finalize,
with two real conditional edges -- the "ask a human instead of guessing" branches that
are the point of this whole module.

* ``route_after_extraction`` reads ``extraction.quality.recommendation``. This is a
  hard stop: ``flag_for_review`` skips classification and triage entirely, rather than
  running them on input the extraction stage already distrusts.
* ``classification_node -> triage_node`` is unconditional: classification's own
  confidence gate doesn't change which nodes run downstream, so it's traced, not forked.
* ``route_after_triage`` reads ``triage.quality.decision``. ``needs_clarification``
  routes to a terminal node that still carries the (provisional) triage result -- never
  withheld, only flagged.
"""

from __future__ import annotations

import functools

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.orchestration import nodes
from app.orchestration.state import AdvisoryState


def route_after_extraction(state: AdvisoryState) -> str:
    assert state.extraction is not None
    if state.extraction.quality.recommendation == "flag_for_review":
        return "needs_extraction_review"
    return "classification"


def route_after_triage(state: AdvisoryState) -> str:
    assert state.triage is not None
    if state.triage.quality.decision == "needs_clarification":
        return "needs_clarification"
    return "finalize"


def _build_graph() -> CompiledStateGraph:
    graph = StateGraph(AdvisoryState)

    graph.add_node("extraction", nodes.extraction_node)
    graph.add_node("classification", nodes.classification_node)
    graph.add_node("triage", nodes.triage_node)
    graph.add_node("finalize", nodes.finalize_node)
    graph.add_node("needs_extraction_review", nodes.needs_extraction_review_node)
    graph.add_node("needs_clarification", nodes.needs_clarification_node)

    graph.set_entry_point("extraction")
    graph.add_conditional_edges(
        "extraction",
        route_after_extraction,
        {"classification": "classification", "needs_extraction_review": "needs_extraction_review"},
    )
    graph.add_edge("classification", "triage")
    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {"finalize": "finalize", "needs_clarification": "needs_clarification"},
    )
    graph.add_edge("finalize", END)
    graph.add_edge("needs_extraction_review", END)
    graph.add_edge("needs_clarification", END)

    return graph.compile()


@functools.lru_cache(maxsize=1)
def get_graph() -> CompiledStateGraph:
    return _build_graph()
