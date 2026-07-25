"""Fetch, parse, and cache MITRE ATT&CK for ICS reference data: techniques (the
classification corpus) and procedure examples (real, labeled attacker-behaviour text).

Source: the official public STIX bundle in mitre-attack/attack-stix-data. We fetch it
once per artifact, keep only the fields the bake-off needs, and cache the result to a
committed file so every later notebook run is offline and reproducible (and does not
re-download / re-parse a multi-MB bundle).

We keep top-level techniques only (IDs like ``T0836``) and drop sub-techniques
(``T0836.001``), revoked, and deprecated objects.

**Leakage guard:** procedure examples are the EVALUATION set only. The embedded
technique *corpus* must stay technique reference text (name/tactics/description) —
never mix procedure text into it, or a method would effectively be matching against
its own answers.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ICS_ATTACK_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "ics-attack/ics-attack.json"
)

# MITRE descriptions embed "(Citation: Foo)" markers and markdown; strip for clean prompts.
_CITATION_RE = re.compile(r"\(Citation:.*?\)", re.DOTALL)
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")  # [text](url) -> text
_WS_RE = re.compile(r"\s+")

_SHORT_DESC_CHARS = 300


@dataclass(frozen=True)
class TechniqueRecord:
    """One ATT&CK-for-ICS technique, reduced to what the bake-off uses."""

    id: str  # e.g. "T0836"
    name: str
    tactics: list[str]  # kill-chain phase names, e.g. ["impair-process-control"]
    description: str  # cleaned + truncated, for compact full-catalogue prompts
    description_full: str  # cleaned but untruncated, for hybrid candidate display


def _clean(text: str) -> str:
    text = _CITATION_RE.sub("", text)
    text = _MD_LINK_RE.sub(r"\1", text)
    return _WS_RE.sub(" ", text).strip()


def _shorten(text: str, limit: int = _SHORT_DESC_CHARS) -> str:
    if len(text) <= limit:
        return text
    clipped = text[:limit]
    # Prefer to end on a sentence boundary, else a word boundary.
    for sep in (". ", " "):
        idx = clipped.rfind(sep)
        if idx > limit * 0.5:
            return clipped[: idx + (1 if sep == ". " else 0)].strip()
    return clipped.strip()


def _external_id(obj: dict) -> str | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack" and "external_id" in ref:
            return ref["external_id"]
    return None


def parse_bundle(bundle: dict) -> list[TechniqueRecord]:
    """Extract top-level technique records from a raw ATT&CK STIX bundle."""
    records: list[TechniqueRecord] = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        tech_id = _external_id(obj)
        if not tech_id or "." in tech_id:  # skip missing IDs and sub-techniques
            continue
        full = _clean(obj.get("description", ""))
        records.append(
            TechniqueRecord(
                id=tech_id,
                name=obj.get("name", "").strip(),
                tactics=[p["phase_name"] for p in obj.get("kill_chain_phases", [])],
                description=_shorten(full),
                description_full=full,
            )
        )
    records.sort(key=lambda r: r.id)
    return records


def fetch_and_cache(cache_path: Path, url: str = ICS_ATTACK_URL) -> list[TechniqueRecord]:
    """Return technique records, loading from ``cache_path`` if it exists.

    On a cache miss, downloads the STIX bundle from ``url``, parses it, writes the
    reduced records to ``cache_path`` (pretty JSON), and returns them. Prints which
    path was taken so the notebook output shows the data's provenance.
    """
    cache_path = Path(cache_path)
    if cache_path.exists():
        print(f"Loaded techniques from cache: {cache_path}")
        return load_cached(cache_path)

    import requests  # imported lazily so parsing/loading needs no network dependency

    print(f"Cache miss — fetching ATT&CK for ICS from:\n  {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    records = parse_bundle(response.json())

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps([asdict(r) for r in records], indent=2), encoding="utf-8"
    )
    print(f"Parsed {len(records)} techniques and cached to: {cache_path}")
    return records


def load_cached(cache_path: Path) -> list[TechniqueRecord]:
    """Load reduced technique records previously written by :func:`fetch_and_cache`."""
    data = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    return [TechniqueRecord(**item) for item in data]


# --- Procedure examples (real, labeled attacker-behaviour text for evaluation) -----

_SOURCE_OBJECT_TYPES = {"intrusion-set", "malware", "tool", "campaign"}


@dataclass(frozen=True)
class ProcedureExample:
    """One real MITRE-documented example of a technique in use.

    MITRE's ATT&CK STIX data links each technique to "uses" relationships from real
    groups/malware/tools/campaigns, each with its own description — e.g. "Sandworm Team
    used Valid Accounts during the 2015 Ukraine Electric Power Attack." These are
    genuine, citation-backed labeled examples, at a scale no hand-written synthetic set
    can match, and are used here as the primary EVALUATION set (never the corpus).
    """

    id: str  # stable id, e.g. "proc-0001"
    technique_id: str  # e.g. "T0822"
    source_name: str  # the group/malware/tool/campaign object this behaviour came from
    behavior_text: str  # cleaned relationship description


def extract_procedure_examples(
    bundle: dict, valid_technique_ids: set[str]
) -> list[ProcedureExample]:
    """Extract procedure examples from a raw ATT&CK STIX bundle.

    Only relationships of type ``uses`` with a non-empty ``description`` and whose
    target is a top-level technique in ``valid_technique_ids`` are kept (matches the
    same top-level-only, non-revoked/deprecated scope as :func:`parse_bundle`).
    """
    technique_id_by_stix_id: dict[str, str] = {}
    source_name_by_stix_id: dict[str, str] = {}
    for obj in bundle.get("objects", []):
        obj_type = obj.get("type")
        if obj_type == "attack-pattern":
            if obj.get("revoked") or obj.get("x_mitre_deprecated"):
                continue
            ext = _external_id(obj)
            if ext and ext in valid_technique_ids:
                technique_id_by_stix_id[obj["id"]] = ext
        elif obj_type in _SOURCE_OBJECT_TYPES:
            source_name_by_stix_id[obj["id"]] = obj.get("name", "").strip()

    examples: list[ProcedureExample] = []
    for obj in bundle.get("objects", []):
        if obj.get("type") != "relationship" or obj.get("relationship_type") != "uses":
            continue
        description = obj.get("description")
        target_ref = obj.get("target_ref", "")
        if not description or target_ref not in technique_id_by_stix_id:
            continue
        examples.append(
            ProcedureExample(
                id=f"proc-{len(examples) + 1:04d}",
                technique_id=technique_id_by_stix_id[target_ref],
                source_name=source_name_by_stix_id.get(obj.get("source_ref", ""), "unknown"),
                behavior_text=_clean(description),
            )
        )
    return examples


def fetch_procedures_and_cache(
    cache_path: Path, valid_technique_ids: set[str], url: str = ICS_ATTACK_URL
) -> list[ProcedureExample]:
    """Return procedure examples, loading from ``cache_path`` (JSONL) if it exists.

    On a cache miss, fetches the STIX bundle fresh (a separate request from
    :func:`fetch_and_cache`'s, since only the raw bundle carries the relationship
    objects), extracts, writes one JSON object per line, and returns them.
    """
    cache_path = Path(cache_path)
    if cache_path.exists():
        print(f"Loaded procedure examples from cache: {cache_path}")
        return load_cached_procedures(cache_path)

    import requests  # imported lazily so parsing/loading needs no network dependency

    print(f"Cache miss — fetching ATT&CK for ICS (procedure examples) from:\n  {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    examples = extract_procedure_examples(response.json(), valid_technique_ids)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(asdict(ex)) + "\n")
    print(f"Extracted {len(examples)} procedure examples and cached to: {cache_path}")
    return examples


def load_cached_procedures(cache_path: Path) -> list[ProcedureExample]:
    """Load procedure examples previously written by :func:`fetch_procedures_and_cache`."""
    examples = []
    with Path(cache_path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                examples.append(ProcedureExample(**json.loads(line)))
    return examples
