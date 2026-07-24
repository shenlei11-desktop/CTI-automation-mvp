"""Named-entity extraction: curated gazetteers + spaCy statistical NER.

Two complementary sources:

1. **Curated gazetteers** (PhraseMatcher, case-insensitive) for the domain-specific
   categories the project cares about — threat actors, ICS/OT vendors, targeted sectors.
   Out-of-the-box NER models do not know that ``VOLTZITE`` is a threat actor or that
   ``Schneider Electric`` is an ICS vendor, and a curated list is more interpretable and
   auditable than a black-box classifier. The lists double as a domain-knowledge artifact.

2. **spaCy statistical NER** for generic ORG / GPE / PERSON entities that provide useful
   context but are not in a gazetteer (e.g. "CISA", a country, a researcher's name).

Gazetteer hits take precedence: where a curated match and a spaCy entity overlap, we keep
the curated (more specific) label. The spaCy model is loaded lazily so importing this
module never triggers a model download.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher

from app.schemas.extraction import EntityType, ExtractionMethod

_GAZETTEER_DIR = Path(__file__).resolve().parents[2] / "data" / "gazetteers"

# gazetteer entity type -> filename
_GAZETTEERS: dict[EntityType, str] = {
    "threat_actor": "threat_actors.txt",
    "ics_vendor": "ics_vendors.txt",
    "sector": "sectors.txt",
}

# spaCy label -> our generic entity type
_SPACY_LABEL_MAP: dict[str, EntityType] = {
    "ORG": "organization",
    "GPE": "location",
    "LOC": "location",
    "PERSON": "person",
}

# General-purpose NER frequently mislabels these technical acronyms / document labels
# as organizations. They carry no analytic value as "entities", so we suppress them
# from the statistical-NER output (gazetteer matches are never affected). Case-folded.
_ENTITY_STOPLIST: frozenset[str] = frozenset(
    s.casefold()
    for s in (
        "CVSS", "CVE", "KEV", "IOC", "IOCs", "TTP", "TTPs", "PoC", "RCE", "DoS", "DDoS",
        "MD5", "SHA-1", "SHA1", "SHA-256", "SHA256",
        "ICS", "OT", "IoT", "PLC", "PLCs", "HMI", "SCADA", "RTU", "DCS", "IED",
        "VPN", "MFA", "API", "URL",
        "ICS Advisory", "Known Exploited Vulnerabilities", "Technical Details",
        "Affected Products", "Summary", "Mitigations",
    )
)

_SPACY_MODEL = "en_core_web_sm"


@dataclass
class RawEntity:
    """An entity before provenance is attached (see extraction.service)."""

    type: EntityType
    text: str
    method: ExtractionMethod
    start: int
    end: int


def _load_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


@functools.lru_cache(maxsize=1)
def get_nlp() -> Language:
    """Load and cache the spaCy pipeline (lazy: only on first extraction)."""
    try:
        return spacy.load(_SPACY_MODEL)
    except OSError as exc:  # model not installed
        raise RuntimeError(
            f"spaCy model '{_SPACY_MODEL}' is not installed. "
            f"Run: python -m spacy download {_SPACY_MODEL}"
        ) from exc


@functools.lru_cache(maxsize=1)
def _get_matcher() -> PhraseMatcher:
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for ent_type, filename in _GAZETTEERS.items():
        patterns = [nlp.make_doc(term) for term in _load_terms(_GAZETTEER_DIR / filename)]
        if patterns:
            matcher.add(ent_type, patterns)
    return matcher


def extract_entities(text: str) -> list[RawEntity]:
    """Extract deduplicated entities from ``text`` with original-text offsets."""
    nlp = get_nlp()
    doc = nlp(text)
    matcher = _get_matcher()

    entities: list[RawEntity] = []
    claimed: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(not (end <= cs or start >= ce) for cs, ce in claimed)

    # 1) Gazetteer matches, longest span first so "water and wastewater" beats "water".
    gaz_matches = sorted(matcher(doc), key=lambda m: m[2] - m[1], reverse=True)
    for match_id, start_tok, end_tok in gaz_matches:
        span = doc[start_tok:end_tok]
        if overlaps(span.start_char, span.end_char):
            continue
        ent_type: EntityType = nlp.vocab.strings[match_id]  # the label we registered
        claimed.append((span.start_char, span.end_char))
        entities.append(
            RawEntity(ent_type, span.text, "gazetteer", span.start_char, span.end_char)
        )

    # 2) spaCy statistical NER for generic entities not already claimed by a gazetteer.
    for ent in doc.ents:
        mapped = _SPACY_LABEL_MAP.get(ent.label_)
        if mapped is None:
            continue
        if ent.text.casefold() in _ENTITY_STOPLIST:
            continue
        if overlaps(ent.start_char, ent.end_char):
            continue
        claimed.append((ent.start_char, ent.end_char))
        entities.append(RawEntity(mapped, ent.text, "spacy_ner", ent.start_char, ent.end_char))

    # Deduplicate by (type, case-folded text), keeping the first occurrence; return in
    # document order.
    seen: set[tuple[str, str]] = set()
    deduped: list[RawEntity] = []
    for ent in sorted(entities, key=lambda e: e.start):
        key = (ent.type, ent.text.casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ent)
    return deduped
