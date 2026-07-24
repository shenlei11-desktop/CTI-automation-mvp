"""Pydantic models for the extraction stage.

These define the public API contract for ``POST /extract`` and, crucially, the
*provenance* model: every extracted fact carries a :class:`SourceSpan` pointing back
to the sentence (and character offsets) it came from. That traceability is a core
requirement of the whole project, so it is baked into the schema from Day 1.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IOCType = Literal["ipv4", "domain", "md5", "sha1", "sha256", "cve"]

EntityType = Literal[
    # Domain-specific (from curated gazetteers)
    "threat_actor",
    "ics_vendor",
    "sector",
    # Generic (from spaCy's statistical NER)
    "organization",
    "location",
    "person",
]

ExtractionMethod = Literal["gazetteer", "spacy_ner"]

Recommendation = Literal["proceed", "flag_for_review"]


class SourceSpan(BaseModel):
    """Where a fact was found in the original report text."""

    sentence: str = Field(..., description="The full sentence containing the fact.")
    start: int = Field(..., description="Character offset of the fact in the original text.")
    end: int = Field(..., description="End character offset (exclusive) in the original text.")


class IOC(BaseModel):
    """A single indicator of compromise, with defang-aware normalization."""

    type: IOCType
    value_raw: str = Field(..., description="The indicator exactly as found (may be defanged).")
    value_normalized: str = Field(..., description="Refanged / canonical form of the indicator.")
    is_private: bool | None = Field(
        None,
        description="For ipv4 only: True if the address is private/reserved (RFC1918 etc.).",
    )
    source: SourceSpan


class Entity(BaseModel):
    """A named entity extracted from the report."""

    type: EntityType
    text: str
    method: ExtractionMethod = Field(
        ..., description="How the entity was found: curated 'gazetteer' or 'spacy_ner'."
    )
    source: SourceSpan


class ExtractionQuality(BaseModel):
    """A lightweight quality summary of an extraction result.

    This is a *metric* only. In Week 2 the extraction agent will branch on
    ``recommendation`` to decide whether to proceed or flag a report for manual
    review; Day 1 just computes and returns the signal.
    """

    n_iocs: int
    n_entities: int
    text_length: int
    signal_density: float = Field(
        ..., description="Extracted facts per 1000 characters of report text."
    )
    recommendation: Recommendation
    reason: str = Field(..., description="Human-readable justification for the recommendation.")


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw report text to extract from.")
    report_id: str | None = Field(
        None, description="Optional caller-supplied identifier, echoed back in the response."
    )


class ExtractResponse(BaseModel):
    report_id: str | None = None
    iocs: list[IOC]
    entities: list[Entity]
    quality: ExtractionQuality
