"""Unit tests for URL fetch + dispatch (pure function, monkeypatched ``requests.get`` --
mirrors the pattern in ``tests/test_triage_kev.py`` so CI never depends on a live
network fetch).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from app.ingestion.models import IngestionError
from app.ingestion.url_fetch import fetch_and_extract

_PDF_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_advisory.pdf"


class _FakeResponse:
    def __init__(self, content_type: str, text: str = "", content: bytes = b""):
        self.headers = {"Content-Type": content_type}
        self.text = text
        self.content = content

    def raise_for_status(self) -> None:
        pass


def test_fetch_and_extract_html(monkeypatch):
    html = (
        "<html><body><article><p>"
        + ("Real advisory content. " * 30)
        + "</p></article></body></html>"
    )
    monkeypatch.setattr(
        "requests.get", lambda *a, **k: _FakeResponse("text/html; charset=utf-8", text=html)
    )
    result = fetch_and_extract("https://example.com/advisory")
    assert "Real advisory content." in result.text


def test_fetch_and_extract_pdf(monkeypatch):
    pdf_bytes = _PDF_FIXTURE.read_bytes()
    monkeypatch.setattr(
        "requests.get",
        lambda *a, **k: _FakeResponse("application/pdf", content=pdf_bytes),
    )
    result = fetch_and_extract("https://example.com/advisory.pdf")
    assert "CVE-2026-9999" in result.text


def test_fetch_and_extract_unsupported_content_type_raises(monkeypatch):
    monkeypatch.setattr(
        "requests.get", lambda *a, **k: _FakeResponse("application/json", text="{}")
    )
    with pytest.raises(IngestionError):
        fetch_and_extract("https://example.com/data.json")


def test_fetch_and_extract_connection_failure_raises(monkeypatch):
    def _raise(*a, **k):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("requests.get", _raise)
    with pytest.raises(IngestionError):
        fetch_and_extract("https://example.com/unreachable")
