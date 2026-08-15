"""Ingestion service: turns a PDF, HTML page, or fetched URL into plain text for the
rest of the pipeline, with a lightweight quality gate mirroring
``app/extraction/service.py``'s ``_assess_quality`` pattern.
"""

from __future__ import annotations

from app.ingestion import html_extract, pdf_extract, url_fetch
from app.ingestion.models import RawIngestResult
from app.schemas.ingestion import IngestQuality, IngestRequest, IngestResponse, IngestSourceType

# Below this length, extraction almost certainly failed or the source was mostly
# boilerplate (nav/ads/an empty article) -- mirrors extraction's own _MIN_TEXT_LENGTH.
_MIN_TEXT_LENGTH = 200


def _assess_quality(text: str) -> IngestQuality:
    if len(text) < _MIN_TEXT_LENGTH:
        return IngestQuality(
            recommendation="flag_for_review",
            reason=(
                f"Extracted only {len(text)} chars of text; extraction likely failed "
                "or the source was mostly boilerplate."
            ),
        )
    return IngestQuality(
        recommendation="proceed", reason=f"Extracted {len(text)} chars of usable text."
    )


def _to_response(raw: RawIngestResult, source_type: IngestSourceType) -> IngestResponse:
    return IngestResponse(
        text=raw.text, title=raw.title, source_type=source_type, quality=_assess_quality(raw.text)
    )


def ingest(request: IngestRequest) -> IngestResponse:
    if request.source_type == "text":
        raw = RawIngestResult(text=request.text or "", title=None)
    elif request.source_type == "html":
        raw = html_extract.extract_text_from_html(request.text or "")
    else:
        raw = url_fetch.fetch_and_extract(request.url or "")

    return _to_response(raw, request.source_type)


def ingest_pdf(data: bytes) -> IngestResponse:
    raw = pdf_extract.extract_text_from_pdf(data)
    return _to_response(raw, "pdf")
