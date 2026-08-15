"""Unit tests for PDF -> text extraction (pure function, no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingestion.models import IngestionError
from app.ingestion.pdf_extract import extract_text_from_pdf

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_advisory.pdf"


def test_extract_text_from_pdf():
    data = _FIXTURE.read_bytes()
    result = extract_text_from_pdf(data)
    assert "CVE-2026-9999" in result.text
    assert "CVSS v3.1 base score of 9.8" in result.text
    assert "VOLTZITE" in result.text


def test_extract_text_from_pdf_invalid_bytes_raises_ingestion_error():
    with pytest.raises(IngestionError):
        extract_text_from_pdf(b"not a real pdf")
