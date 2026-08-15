"""Load the MITRE ATT&CK-for-ICS technique reference corpus.

This is committed reference data (`data/classification/attack_ics_techniques.json`),
not something refreshed at request time — the corpus only changes when MITRE updates
the ATT&CK-for-ICS matrix, which is a maintenance event, not a runtime one. To
regenerate it, run `research/lib/attack_data.fetch_and_cache` against this file's path
(that function still fetches live from MITRE's STIX bundle; it is intentionally not
duplicated here, since this module has no reason to ever touch the network).
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path

_CORPUS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "classification" / "attack_ics_techniques.json"
)


@dataclass(frozen=True)
class TechniqueRecord:
    """One ATT&CK-for-ICS technique."""

    id: str  # e.g. "T0836"
    name: str
    tactics: list[str]  # kill-chain phase names, e.g. ["impair-process-control"]
    description: str  # short/truncated — used for the embedding corpus text
    description_full: str  # untruncated — used for reranker candidate text
    url: str  # canonical https://attack.mitre.org/techniques/<id> page
    mitigation: str  # course-of-action text — display only, not used for matching
    # (it describes the fix, not attacker behaviour, so it wouldn't help retrieval or
    # reranking; see research/lib/attack_data.py's module docstring for the measured
    # reasoning). "" if MITRE has no linked mitigation for this technique.


@functools.lru_cache(maxsize=1)
def get_techniques() -> list[TechniqueRecord]:
    """Load the committed technique corpus (cached after first call)."""
    if not _CORPUS_PATH.exists():
        raise RuntimeError(
            f"Technique corpus not found at {_CORPUS_PATH}. Regenerate it via "
            "research/lib/attack_data.fetch_and_cache(<this path>)."
        )
    data = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    return [TechniqueRecord(**item) for item in data]


@functools.lru_cache(maxsize=1)
def get_technique_by_id() -> dict[str, TechniqueRecord]:
    """Lookup dict for the technique corpus, keyed by technique ID."""
    return {t.id: t for t in get_techniques()}
