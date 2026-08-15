"""Live CISA ICS advisory feed, for the demo page's "fetch a real advisory" feature.

Verified live: ``https://www.cisa.gov/cybersecurity-advisories/all.xml`` is a real RSS
2.0 feed, returns HTTP 200 with the default ``requests`` User-Agent (no spoofing or API
key needed), and typically carries ~30 items of which most are ICS advisories
(filtered here on ``/ics-advisories/`` appearing in the item's link -- the feed also
carries non-ICS cybersecurity advisories we don't want).

Mirrors ``app/triage/kev.py``'s use of ``requests`` with an explicit timeout. Unlike
KEV's live-refresh (which has a cached snapshot to fall back to), a fetch failure here
has nothing to fall back to -- it's surfaced as an ``IngestionError`` so the caller
(the route layer) can turn it into a clear error, and the frontend degrades to its
canned examples.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from app.ingestion.models import IngestionError
from app.schemas.ingestion import FeedItem

FEED_URL = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
_FETCH_TIMEOUT_SECONDS = 15
_ICS_LINK_MARKER = "/ics-advisories/"


def fetch_ics_advisories(limit: int = 10, url: str = FEED_URL) -> list[FeedItem]:
    try:
        response = requests.get(url, timeout=_FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise IngestionError(f"Could not fetch the CISA advisory feed: {exc}") from exc

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise IngestionError(f"CISA advisory feed was not valid XML: {exc}") from exc

    items: list[FeedItem] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        title = (item.findtext("title") or "").strip()
        if not link or not title or _ICS_LINK_MARKER not in link:
            continue
        items.append(
            FeedItem(title=title, url=link, published=item.findtext("pubDate"))
        )
        if len(items) >= limit:
            break

    return items
