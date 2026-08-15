"""Fetch a report from a URL and dispatch to the right extractor by content type.

Mirrors ``app/triage/kev.py``'s use of ``requests`` with an explicit timeout, but
unlike KEV's live-refresh (which has a cached snapshot to fall back to), a fetch
failure here has nothing to fall back to -- it's surfaced to the caller as an
``IngestionError`` rather than swallowed.
"""

from __future__ import annotations

import requests

from app.ingestion.html_extract import extract_text_from_html
from app.ingestion.models import IngestionError, RawIngestResult
from app.ingestion.pdf_extract import extract_text_from_pdf

_FETCH_TIMEOUT_SECONDS = 15


def fetch_and_extract(url: str) -> RawIngestResult:
    try:
        response = requests.get(url, timeout=_FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"Could not fetch {url!r}: {exc}") from exc

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" in content_type:
        return extract_text_from_pdf(response.content)
    if "html" in content_type or not content_type:
        return extract_text_from_html(response.text)
    raise IngestionError(f"Unsupported content type {content_type!r} at {url!r}.")
