"""Pydantic models for the ingestion stage.

Turns a PDF, an HTML page, or a fetched URL into the plain text the rest of the
pipeline already expects. PDF is handled by a separate route with a multipart body
(see ``app/api/routes/ingestion.py``), so it isn't a valid ``source_type`` here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.extraction import Recommendation

IngestSourceType = Literal["text", "html", "url", "pdf"]


class IngestRequest(BaseModel):
    source_type: Literal["text", "html", "url"]
    text: str | None = Field(
        None, description="Raw text ('text' mode) or raw HTML ('html' mode)."
    )
    url: str | None = Field(None, description="URL to fetch ('url' mode).")

    @model_validator(mode="after")
    def _check_payload_matches_source_type(self) -> IngestRequest:
        if self.source_type in ("text", "html") and not self.text:
            raise ValueError(f"source_type={self.source_type!r} requires 'text'.")
        if self.source_type == "url" and not self.url:
            raise ValueError("source_type='url' requires 'url'.")
        return self


class IngestQuality(BaseModel):
    recommendation: Recommendation
    reason: str = Field(..., description="Human-readable justification for the recommendation.")


class IngestResponse(BaseModel):
    text: str
    title: str | None = None
    source_type: IngestSourceType
    quality: IngestQuality
