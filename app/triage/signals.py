"""Lightweight text signals triage needs that extraction doesn't provide today:
CVSS mentions, exposure level, and asset-criticality tier.

Curated phrase lists in ``data/triage/`` mirror ``data/gazetteers/`` exactly. Plain
case-insensitive substring matching is enough here (no spaCy ``PhraseMatcher``) since
these are short, hand-curated lists, not large open-ended gazetteers.

Reconciliation is where "clearly specified" gets decided: no hits -> unknown; hits in
exactly one category -> that category; hits in *both* categories -> unknown. A report
that says both "the interface is internet-facing" and "operators should segment the
network" cannot be resolved by keyword matching alone (it can't tell current state from
a recommendation) -- and unknown is the *safer* failure mode here, since it routes to
"ask a human" rather than silently picking the wrong current state.
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.extraction.ioc import RawIOC
from app.extraction.provenance import Sentence

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "triage"

# Matches "CVSS v3.1 base score of 9.8", "CVSS score: 7.5", "CVSS 9.8".
_CVSS_RE = re.compile(
    r"CVSS(?:\s*v[234](?:\.\d)?)?\s*(?:(?:base\s*)?score\s*)?(?:of|is|[:=])?\s*(\d{1,2}(?:\.\d)?)",
    re.IGNORECASE,
)

ExposureCategory = Literal["internet_facing", "segmented"]
AssetTierCategory = Literal["safety_critical", "process_critical", "monitoring_only"]


@dataclass
class RawCVSSMention:
    score: float
    start: int
    end: int


@dataclass
class RawKeywordHit:
    category: str
    phrase: str
    start: int
    end: int


def _load_phrases(filename: str) -> list[str]:
    path = _DATA_DIR / filename
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


@functools.lru_cache(maxsize=1)
def _exposure_phrase_lists() -> dict[str, list[str]]:
    return {
        "internet_facing": _load_phrases("exposure_internet_facing.txt"),
        "segmented": _load_phrases("exposure_segmented.txt"),
    }


@functools.lru_cache(maxsize=1)
def _asset_tier_phrase_lists() -> dict[str, list[str]]:
    return {
        "safety_critical": _load_phrases("asset_tier_safety_critical.txt"),
        "process_critical": _load_phrases("asset_tier_process_critical.txt"),
        "monitoring_only": _load_phrases("asset_tier_monitoring_only.txt"),
    }


def _find_phrase_hits(text: str, phrase_lists: dict[str, list[str]]) -> list[RawKeywordHit]:
    hits = []
    lower_text = text.lower()
    for category, phrases in phrase_lists.items():
        for phrase in phrases:
            phrase_lower = phrase.lower()
            start = 0
            while True:
                idx = lower_text.find(phrase_lower, start)
                if idx == -1:
                    break
                hits.append(RawKeywordHit(category, phrase, idx, idx + len(phrase)))
                start = idx + 1
    hits.sort(key=lambda h: h.start)
    return hits


def detect_cvss_mentions(text: str) -> list[RawCVSSMention]:
    """Extract CVSS score mentions, validated to the real 0.0-10.0 range."""
    mentions = []
    for m in _CVSS_RE.finditer(text):
        try:
            score = float(m.group(1))
        except ValueError:
            continue
        if 0.0 <= score <= 10.0:
            mentions.append(RawCVSSMention(score, m.start(), m.end()))
    return mentions


def detect_exposure_signals(text: str) -> list[RawKeywordHit]:
    return _find_phrase_hits(text, _exposure_phrase_lists())


def detect_asset_tier_signals(text: str) -> list[RawKeywordHit]:
    return _find_phrase_hits(text, _asset_tier_phrase_lists())


def _resolve_single_category(hits: list[RawKeywordHit]) -> tuple[str, RawKeywordHit | None]:
    """No hits, or hits spanning >1 category -> unknown. Exactly one category ->
    that category, paired with its earliest hit."""
    categories = {h.category for h in hits}
    if len(categories) != 1:
        return "unknown", None
    category = categories.pop()
    first = min((h for h in hits if h.category == category), key=lambda h: h.start)
    return category, first


def resolve_exposure(hits: list[RawKeywordHit]) -> tuple[str, RawKeywordHit | None]:
    return _resolve_single_category(hits)


def resolve_asset_tier(hits: list[RawKeywordHit]) -> tuple[str, RawKeywordHit | None]:
    return _resolve_single_category(hits)


def associate_cvss_to_cves(
    cve_iocs: list[RawIOC], cvss_mentions: list[RawCVSSMention], sentences: list[Sentence]
) -> dict[str, RawCVSSMention | None]:
    """Associate each CVE (by normalized value) with a CVSS mention, if any.

    Pairs a CVE and a CVSS mention when they co-occur in the same sentence. If exactly
    one CVE and one CVSS mention exist anywhere in the text (the common
    single-CVE-advisory case), pairs them by default. Otherwise leaves a CVE
    unassociated rather than guess a wrong pairing.
    """
    result: dict[str, RawCVSSMention | None] = {cve.value_normalized: None for cve in cve_iocs}
    if not cve_iocs or not cvss_mentions:
        return result

    if len(cve_iocs) == 1 and len(cvss_mentions) == 1:
        result[cve_iocs[0].value_normalized] = cvss_mentions[0]
        return result

    def sentence_at(offset: int) -> Sentence | None:
        for s in sentences:
            if s.start <= offset < s.end:
                return s
        return None

    for cve in cve_iocs:
        cve_sentence = sentence_at(cve.start)
        if cve_sentence is None:
            continue
        for mention in cvss_mentions:
            if sentence_at(mention.start) is cve_sentence:
                result[cve.value_normalized] = mention
                break
    return result
