"""CISA Known Exploited Vulnerabilities (KEV) catalog: fetch, cache, lookup.

The only live external network dependency in the whole app. A committed snapshot
(``data/kev/kev_catalog.json``) means the app works fully offline and demos reliably;
a live refresh is attempted only when the cache is stale, and any failure falls back
to the snapshot silently -- this must never crash or block a request.

Mirrors ``research/lib/attack_data.py``'s fetch/cache/parse shape.
"""

from __future__ import annotations

import functools
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "kev" / "kev_catalog.json"

# Only refresh from the live feed if the committed/cached snapshot is older than this.
_KEV_CACHE_TTL_HOURS = 24

KEVStatus = Literal["listed", "not_listed", "unknown"]


@dataclass(frozen=True)
class KEVEntry:
    cve_id: str
    date_added: str
    vendor_project: str
    product: str
    known_ransomware_use: str


@dataclass(frozen=True)
class KEVCatalog:
    entries: dict[str, KEVEntry]  # keyed by cve_id, upper-cased
    date_released: str | None  # None only if no data was ever available (see get_kev_catalog)


def _parse_feed(data: dict) -> tuple[list[KEVEntry], str]:
    entries = [
        KEVEntry(
            cve_id=v["cveID"].upper(),
            date_added=v.get("dateAdded", ""),
            vendor_project=v.get("vendorProject", ""),
            product=v.get("product", ""),
            known_ransomware_use=v.get("knownRansomwareCampaignUse", "Unknown"),
        )
        for v in data.get("vulnerabilities", [])
    ]
    return entries, data.get("dateReleased", "")


def fetch_and_cache(
    cache_path: Path = _CATALOG_PATH, url: str = KEV_URL
) -> tuple[list[KEVEntry], str]:
    """Fetch the live KEV feed, cache it (trimmed to the fields triage uses), and
    return the entries plus the catalog's ``dateReleased`` for audit trails."""
    import requests  # imported lazily so loading needs no network dependency

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    entries, date_released = _parse_feed(response.json())

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {"date_released": date_released, "entries": [asdict(e) for e in entries]}, indent=1
        ),
        encoding="utf-8",
    )
    return entries, date_released


def load_cached(cache_path: Path = _CATALOG_PATH) -> tuple[list[KEVEntry], str] | None:
    """Load the committed/cached snapshot, or None if it doesn't exist yet."""
    if not cache_path.exists():
        return None
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    entries = [KEVEntry(**item) for item in data["entries"]]
    return entries, data["date_released"]


def _cache_age_hours(cache_path: Path) -> float:
    return (time.time() - cache_path.stat().st_mtime) / 3600


@functools.lru_cache(maxsize=1)
def get_kev_catalog() -> KEVCatalog:
    """The runtime accessor: refreshes from the live feed only if the cache is stale,
    falling back to the (possibly stale) cache on any fetch failure. Returns an empty,
    ``date_released=None`` catalog only if there is neither a live fetch nor any cache
    at all -- never raises, never blocks a request indefinitely.
    """
    cached = load_cached()
    is_stale = cached is None or _cache_age_hours(_CATALOG_PATH) > _KEV_CACHE_TTL_HOURS

    if is_stale:
        try:
            entries, date_released = fetch_and_cache()
            return KEVCatalog(entries={e.cve_id: e for e in entries}, date_released=date_released)
        except Exception:
            pass  # fall through to the cached snapshot, or the empty sentinel below

    if cached is not None:
        entries, date_released = cached
        return KEVCatalog(entries={e.cve_id: e for e in entries}, date_released=date_released)

    return KEVCatalog(entries={}, date_released=None)


def lookup(catalog: KEVCatalog, cve_id: str) -> KEVStatus:
    """Status for one CVE against an already-loaded catalog.

    ``"not_listed"`` means a catalog (fresh or stale-but-present) was actually
    consulted and the CVE wasn't in it. ``"unknown"`` means no catalog data was
    available at all -- these are deliberately distinct, and the distinction (plus the
    catalog's ``date_released``) belongs in the caller's audit trail.
    """
    if catalog.date_released is None:
        return "unknown"
    return "listed" if cve_id.upper() in catalog.entries else "not_listed"
