"""End-to-end tests for /ingest and /ingest/pdf.

No spaCy/fastembed model dependency (trafilatura + pypdf + regex only), so these run
unconditionally. The URL-mode test monkeypatches ``requests.get`` -- mirrors
``tests/test_triage_kev.py`` -- so CI never depends on a live network fetch.
"""

from __future__ import annotations

from pathlib import Path

_PDF_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_advisory.pdf"


def test_ingest_text_passthrough(client):
    resp = client.post("/ingest", json={"source_type": "text", "text": "A" * 250})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_type"] == "text"
    assert data["quality"]["recommendation"] == "proceed"
    assert len(data["text"]) == 250


def test_ingest_html_strips_boilerplate(client):
    html = (
        "<html><head><title>Test Advisory</title></head><body>"
        "<nav>Home | Contact</nav><article><p>"
        + ("Real advisory content about a CVE and a CVSS score. " * 10)
        + "</p></article><footer>Copyright</footer></body></html>"
    )
    resp = client.post("/ingest", json={"source_type": "html", "text": html})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Advisory"
    assert "Real advisory content" in data["text"]
    assert "Contact" not in data["text"]


def test_ingest_url_mode(client, monkeypatch):
    html = (
        "<html><body><article><p>"
        + ("Fetched advisory content. " * 20)
        + "</p></article></body></html>"
    )

    class _FakeResponse:
        headers = {"Content-Type": "text/html; charset=utf-8"}
        text = html

        def raise_for_status(self) -> None:
            pass

    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse())

    resp = client.post("/ingest", json={"source_type": "url", "url": "https://example.com/advisory"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_type"] == "url"
    assert "Fetched advisory content." in data["text"]


def test_ingest_url_fetch_failure_returns_422(client, monkeypatch):
    import requests

    def _raise(*a, **k):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("requests.get", _raise)

    resp = client.post("/ingest", json={"source_type": "url", "url": "https://example.com/dead"})
    assert resp.status_code == 422


def test_ingest_missing_payload_for_source_type_rejected(client):
    resp = client.post("/ingest", json={"source_type": "url"})
    assert resp.status_code == 422


def test_ingest_pdf_upload(client):
    with _PDF_FIXTURE.open("rb") as f:
        resp = client.post(
            "/ingest/pdf", files={"file": ("sample_advisory.pdf", f, "application/pdf")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_type"] == "pdf"
    assert "CVE-2026-9999" in data["text"]


def test_ingest_pdf_invalid_file_returns_422(client):
    resp = client.post(
        "/ingest/pdf", files={"file": ("bad.pdf", b"not a real pdf", "application/pdf")}
    )
    assert resp.status_code == 422


_SAMPLE_FEED_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<item>
  <title>Siemens Parasolid</title>
  <link>https://www.cisa.gov/news-events/ics-advisories/icsa-26-225-10</link>
  <description>ignored</description>
  <pubDate>Thu, 13 Aug 26 12:00:00 +0000</pubDate>
</item>
</channel></rss>
"""


def test_ingest_feed(client, monkeypatch):
    class _FakeResponse:
        content = _SAMPLE_FEED_XML

        def raise_for_status(self) -> None:
            pass

    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse())

    resp = client.get("/ingest/feed?limit=5")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Siemens Parasolid"
    assert "/ics-advisories/" in items[0]["url"]


def test_ingest_feed_fetch_failure_returns_502(client, monkeypatch):
    import requests

    def _raise(*a, **k):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("requests.get", _raise)

    resp = client.get("/ingest/feed")
    assert resp.status_code == 502
