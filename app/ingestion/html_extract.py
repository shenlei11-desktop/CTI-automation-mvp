"""HTML -> plain text extraction via ``trafilatura``.

Strips navigation, ads, and boilerplate to isolate the actual report body. CISA
advisories and Dragos posts don't share a page layout, so a naive ``<p>``-tag scrape
would need per-site tuning; trafilatura's general-purpose main-content extraction
avoids that.
"""

from __future__ import annotations

import trafilatura

from app.ingestion.models import RawIngestResult


def extract_text_from_html(html: str) -> RawIngestResult:
    document = trafilatura.bare_extraction(html, with_metadata=True)
    if document is None or not document.text:
        return RawIngestResult(text="", title=None)
    return RawIngestResult(text=document.text, title=document.title)
