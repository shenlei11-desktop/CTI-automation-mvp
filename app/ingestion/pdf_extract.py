"""PDF -> plain text extraction via ``pypdf``.

Known limitation: table-heavy layout (e.g. an affected-versions table) may not
extract in reading order -- acceptable here since the pipeline's "paste text
directly" path always remains available as a fallback.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.ingestion.models import IngestionError, RawIngestResult


def extract_text_from_pdf(data: bytes) -> RawIngestResult:
    try:
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError as exc:
        raise IngestionError(f"Could not read PDF: {exc}") from exc

    title = reader.metadata.title if reader.metadata else None
    return RawIngestResult(text=text.strip(), title=title)
