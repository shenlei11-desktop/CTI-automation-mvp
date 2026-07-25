"""Unified evaluation dataset: MITRE procedure examples + synthetic + real excerpts.

Three sources, each tagged with a ``slice``:

- ``"procedure"`` — real, MITRE-documented examples of a technique in use (via
  :mod:`lib.attack_data`'s ``ProcedureExample``). Single true technique each, ~238
  available across 72/79 techniques. The primary eval set — large enough to actually
  rank methods against each other.
- ``"synthetic-easy"`` / ``"synthetic-hard"`` — the hand-written examples in
  ``labeled_dataset.jsonl`` (may be multi-label), tagged by their existing
  ``difficulty`` field.
- ``"real"`` — the user's own real-report excerpts in the gitignored
  ``labeled_dataset.local.jsonl``, if present.

**Leakage guard:** these are the EVALUATION set. The embedded technique corpus must
stay technique reference text only — see :func:`assert_no_leakage`.

**Name-absent slice:** for each example, ``name_absent`` is True when none of its true
techniques' names appear verbatim in its behaviour text. This is a data-driven,
at-scale replacement for a hand-labeled easy/hard split — a direct, objective measure
of whether a method's score depends on lexical overlap with the technique's own name.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path

from . import attack_data


@dataclass(frozen=True)
class EvalExample:
    id: str
    slice: str  # "procedure" | "synthetic-easy" | "synthetic-hard" | "real"
    true_technique_ids: list[str]
    behavior_text: str
    source: str  # attribution: MITRE source object, or the dataset's source_citation
    name_absent: bool = False  # computed by compute_name_absent(); default until then


def load_procedure_examples(path: Path) -> list[EvalExample]:
    """Load MITRE procedure examples as unified eval examples (slice="procedure")."""
    return [
        EvalExample(
            id=p.id,
            slice="procedure",
            true_technique_ids=[p.technique_id],
            behavior_text=p.behavior_text,
            source=p.source_name,
        )
        for p in attack_data.load_cached_procedures(path)
    ]


def _load_dataset_jsonl(path: Path, slice_for_row) -> list[EvalExample]:
    if not Path(path).exists():
        return []
    examples = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            examples.append(
                EvalExample(
                    id=row["id"],
                    slice=slice_for_row(row),
                    true_technique_ids=row["true_technique_ids"],
                    behavior_text=row["behavior_text"],
                    source=row.get("source_citation") or row.get("source_type", "synthetic"),
                )
            )
    return examples


def load_synthetic_examples(path: Path) -> list[EvalExample]:
    """Load ``labeled_dataset.jsonl`` rows, tagged by their existing difficulty field."""
    return _load_dataset_jsonl(path, lambda row: f"synthetic-{row.get('difficulty', 'easy')}")


def load_real_examples(path: Path) -> list[EvalExample]:
    """Load the user's gitignored real-excerpt rows, if the file exists (empty list if not)."""
    return _load_dataset_jsonl(path, lambda row: "real")


def load_eval_set(
    procedures_path: Path, synthetic_path: Path, real_path: Path
) -> list[EvalExample]:
    """Load and concatenate all three eval slices."""
    return (
        load_procedure_examples(procedures_path)
        + load_synthetic_examples(synthetic_path)
        + load_real_examples(real_path)
    )


def validate_technique_ids(examples: list[EvalExample], valid_ids: set[str]) -> None:
    """Loud failure on a typo'd technique ID, rather than a silent scoring miss."""
    for ex in examples:
        unknown = set(ex.true_technique_ids) - valid_ids
        if unknown:
            raise ValueError(f"{ex.id} ({ex.slice}): unknown technique IDs {unknown}")


def compute_name_absent(
    examples: list[EvalExample], technique_by_id: dict[str, attack_data.TechniqueRecord]
) -> list[EvalExample]:
    """Return new examples with ``name_absent`` set: True when none of an example's true
    technique names appear (case-insensitive) in its behaviour text.
    """
    updated = []
    for ex in examples:
        names = [
            technique_by_id[tid].name.lower()
            for tid in ex.true_technique_ids
            if tid in technique_by_id
        ]
        text_lower = ex.behavior_text.lower()
        absent = not any(name in text_lower for name in names)
        updated.append(replace(ex, name_absent=absent))
    return updated


def assert_no_leakage(corpus_texts: list[str], examples: list[EvalExample]) -> None:
    """Defensive check: no eval example's behaviour text is verbatim present in the
    embedded corpus. Guards against accidentally mixing eval text into the technique
    corpus, which would let a retrieval method match against its own answer key.
    """
    corpus_set = set(corpus_texts)
    leaked = [ex.id for ex in examples if ex.behavior_text in corpus_set]
    if leaked:
        raise ValueError(f"Leakage detected — eval text also present in corpus: {leaked}")


def sample_by_technique(
    examples: list[EvalExample], n: int, seed: int = 42
) -> list[EvalExample]:
    """Deterministic stratified sample of size ``n``.

    Groups examples by their first true technique ID and round-robins across groups
    (after seeded shuffling of both group order and within-group order), so a
    cost-limited sample still spreads across as much of the technique space as
    possible — plain random sampling would bias toward techniques with many procedure
    examples (some have 5+; most synthetic/real examples have exactly 1).
    """
    if n >= len(examples):
        return list(examples)

    rng = random.Random(seed)
    groups: dict[str, list[EvalExample]] = defaultdict(list)
    for ex in examples:
        key = ex.true_technique_ids[0] if ex.true_technique_ids else "unknown"
        groups[key].append(ex)
    for group in groups.values():
        rng.shuffle(group)

    group_keys = sorted(groups.keys())
    rng.shuffle(group_keys)

    sampled: list[EvalExample] = []
    idx = 0
    while len(sampled) < n and any(groups[k] for k in group_keys):
        key = group_keys[idx % len(group_keys)]
        if groups[key]:
            sampled.append(groups[key].pop())
        idx += 1
    return sampled
