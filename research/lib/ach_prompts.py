"""Prompt builder for Method E — an ACH-style arbiter over Method D's candidates.

Analysis of Competing Hypotheses (ACH, Heuer) is the structured-analytic-technique
answer to reasoning under uncertainty: given a fixed hypothesis space, weigh evidence
for *and against* each hypothesis, then favour the one with the LEAST disconfirming
evidence — not simply the one with the most supporting evidence, which is what an
unstructured "just pick the best match" prompt tends to produce.

This module only builds the prompt. Parsing reuses `ollama_client.parse_prediction`
unmodified — it already tolerates extra per-entry keys (`evidence_for`,
`evidence_against`, `verdict`) alongside the `technique_id`/`rank` it actually reads,
so the ACH-shaped response needs no new parsing code (verified by reading
`_coerce_id_list`: unrecognised dict keys are simply ignored, not rejected).

Deliberately NOT a naive "rank all 79 techniques" prompt (Method B's shape) — the 2026
open-source-LLM ATT&CK classification study found that shape weak even at 236B params
(micro-F1 0.22) and that retrieval grounding, not prompt engineering, is what actually
helps (RAG raised F1 to 0.32). So the hypothesis space here is always Method D's
already-retrieved-and-reranked top-K candidates, never the full corpus — the arbiter
reasons *among* strong candidates, it doesn't generate or search for them.
"""

from __future__ import annotations

_ACH_FORMAT = """For EACH candidate above, weigh the evidence for and against it being the
technique this behaviour describes — the same discipline an intelligence analyst uses
under Analysis of Competing Hypotheses: a hypothesis survives on how little evidence
contradicts it, not on how much sounds plausible at first glance. Then rank all
candidates by that survival, best (least disconfirming evidence) first.

Reply with ONLY this JSON shape, one entry per candidate listed above (all of them, in
your ranked order — do not omit any):
{"predicted_techniques": [
  {"technique_id": "<id>", "rank": 1,
   "evidence_for": "<specific phrase(s) in the behaviour that support this technique>",
   "evidence_against": "<specific reason(s) this technique might be the wrong call, or \
the word none if you find no disconfirming evidence>",
   "verdict": "supported" | "weakly_supported" | "not_supported"}
]}
Use only the technique IDs listed in the candidates above — do not introduce any other
technique ID."""


def build_ach_prompt(behavior_text: str, candidates: list[tuple[str, str, str]]) -> str:
    """Build the ACH-arbiter prompt for one behaviour over its retrieved candidates.

    `candidates` is Method D's retrieve+rerank output for this behaviour, as
    `(technique_id, name, description_full)` tuples in reranked (best-first) order —
    that order is shown to the model as a hint, not authority; the arbiter is asked to
    re-derive its own ranking from the evidence, not simply confirm the reranker's.
    """
    lines = [f"{tid}: {name} - {desc}" for tid, name, desc in candidates]
    catalogue = "\n".join(lines)
    return f"""You are a cyber threat intelligence analyst mapping attacker behaviour to \
MITRE ATT&CK for ICS techniques.

CANDIDATE TECHNIQUES (shortlisted by a retrieval system, in its ranked order — treat \
this order as a starting hint, not a verdict):
{catalogue}

BEHAVIOUR TO CLASSIFY:
"{behavior_text}"

{_ACH_FORMAT}"""
