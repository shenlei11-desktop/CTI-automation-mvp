"""Unit tests for the live CISA advisory feed (pure function, monkeypatched
``requests.get`` -- mirrors the pattern in ``tests/test_triage_kev.py`` so CI never
depends on a live network fetch).
"""

from __future__ import annotations

import pytest
import requests

from app.ingestion.feed import fetch_ics_advisories
from app.ingestion.models import IngestionError

_SAMPLE_FEED_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
<title>All CISA Advisories</title>
<item>
  <title>Siemens Parasolid</title>
  <link>https://www.cisa.gov/news-events/ics-advisories/icsa-26-225-10</link>
  <description>&lt;p&gt;Out of bounds read&lt;/p&gt;</description>
  <pubDate>Thu, 13 Aug 26 12:00:00 +0000</pubDate>
</item>
<item>
  <title>Some Non-ICS Advisory</title>
  <link>https://www.cisa.gov/news-events/cybersecurity-advisories/aa26-097a</link>
  <description>&lt;p&gt;Not an ICS advisory&lt;/p&gt;</description>
  <pubDate>Wed, 12 Aug 26 12:00:00 +0000</pubDate>
</item>
<item>
  <title>Johnson Controls Metasys</title>
  <link>https://www.cisa.gov/news-events/ics-advisories/icsa-26-225-14</link>
  <description>&lt;p&gt;Something else&lt;/p&gt;</description>
  <pubDate>Thu, 13 Aug 26 12:00:00 +0000</pubDate>
</item>
</channel></rss>
"""


class _FakeResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        pass


def test_fetch_ics_advisories_filters_to_ics_only(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(_SAMPLE_FEED_XML))
    items = fetch_ics_advisories(limit=10)
    assert len(items) == 2
    assert all("/ics-advisories/" in item.url for item in items)
    assert items[0].title == "Siemens Parasolid"
    assert items[0].published == "Thu, 13 Aug 26 12:00:00 +0000"


def test_fetch_ics_advisories_respects_limit(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(_SAMPLE_FEED_XML))
    items = fetch_ics_advisories(limit=1)
    assert len(items) == 1


def test_fetch_ics_advisories_connection_failure_raises(monkeypatch):
    def _raise(*a, **k):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("requests.get", _raise)
    with pytest.raises(IngestionError):
        fetch_ics_advisories()


def test_fetch_ics_advisories_invalid_xml_raises(monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(b"not xml at all <<<"))
    with pytest.raises(IngestionError):
        fetch_ics_advisories()


def test_fetch_ics_advisories_empty_feed_returns_empty_list(monkeypatch):
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse(empty))
    assert fetch_ics_advisories() == []
