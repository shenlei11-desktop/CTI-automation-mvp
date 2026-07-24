"""Extraction service: orchestrates IOC + entity extraction and provenance.

This is the single entry point the API calls. It runs IOC and entity extraction,
attaches source-sentence provenance to every fact, and computes a lightweight
``ExtractionQuality`` summary.

Note on the quality summary: it is a *metric only* for Day 1. In Week 2 the extraction
agent will branch on ``recommendation`` (proceed vs flag-for-review); here we simply
compute and expose the signal so that later decision has something honest to consume.
The thresholds below are deliberately explicit and named rather than magic numbers.
"""

from __future__ import annotations

from app.extraction import ioc as ioc_mod
from app.extraction import ner as ner_mod
from app.extraction import provenance as prov
from app.schemas.extraction import (
    IOC,
    Entity,
    ExtractionQuality,
    ExtractResponse,
)

# Below this length, the input is almost certainly a stub or a failed parse.
_MIN_TEXT_LENGTH = 200
# We need at least this many extracted facts to triage a report with any confidence.
_MIN_TOTAL_SIGNAL = 1


def _assess_quality(text: str, n_iocs: int, n_entities: int) -> ExtractionQuality:
    text_length = len(text)
    total = n_iocs + n_entities
    density = round(total / (text_length / 1000), 3) if text_length else 0.0

    if text_length < _MIN_TEXT_LENGTH:
        recommendation = "flag_for_review"
        reason = (
            f"Report text is very short ({text_length} chars); "
            "likely a parsing failure or a stub rather than a full report."
        )
    elif total < _MIN_TOTAL_SIGNAL:
        recommendation = "flag_for_review"
        reason = "No IOCs or entities were extracted; too little signal to triage confidently."
    else:
        recommendation = "proceed"
        reason = (
            f"Extracted {n_iocs} IOC(s) and {n_entities} entity(ies) from "
            f"{text_length} chars of text."
        )

    return ExtractionQuality(
        n_iocs=n_iocs,
        n_entities=n_entities,
        text_length=text_length,
        signal_density=density,
        recommendation=recommendation,
        reason=reason,
    )


def extract(text: str, report_id: str | None = None) -> ExtractResponse:
    """Run the full extraction stage over ``text`` and return a structured response."""
    sentences = prov.build_sentence_index(text)

    raw_iocs = ioc_mod.extract_iocs(text)
    raw_entities = ner_mod.extract_entities(text)

    # A token already identified as a concrete IOC should not also be reported as a
    # generic (statistical-NER) entity — e.g. spaCy tagging "CVE-2026" as an ORG when
    # the IOC extractor already captured the full CVE "CVE-2026-2841". We suppress a
    # spaCy entity when it either overlaps an IOC span or is a prefix of an IOC value
    # (the latter catches a second textual occurrence the deduplicated span would miss).
    # Gazetteer hits are always kept.
    ioc_spans = [(r.start, r.end) for r in raw_iocs]
    ioc_values = {v for r in raw_iocs for v in (r.value_raw, r.value_normalized) if v}

    def _overlaps_ioc(start: int, end: int) -> bool:
        return any(not (end <= cs or start >= ce) for cs, ce in ioc_spans)

    def _is_partial_ioc(text: str) -> bool:
        token = text.strip()
        return bool(token) and any(value.startswith(token) for value in ioc_values)

    raw_entities = [
        r
        for r in raw_entities
        if r.method != "spacy_ner"
        or not (_overlaps_ioc(r.start, r.end) or _is_partial_ioc(r.text))
    ]

    iocs = [
        IOC(
            type=raw.type,
            value_raw=raw.value_raw,
            value_normalized=raw.value_normalized,
            is_private=raw.is_private,
            source=prov.locate(sentences, raw.start, raw.end),
        )
        for raw in raw_iocs
    ]

    entities = [
        Entity(
            type=raw.type,
            text=raw.text,
            method=raw.method,
            source=prov.locate(sentences, raw.start, raw.end),
        )
        for raw in raw_entities
    ]

    quality = _assess_quality(text, len(iocs), len(entities))
    return ExtractResponse(report_id=report_id, iocs=iocs, entities=entities, quality=quality)
