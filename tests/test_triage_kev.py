"""Unit tests for CISA KEV catalog fetch/cache/lookup.

The bundled sample advisory's CVE-2026-2841 is fictional and can never appear in the
real CISA feed, so testing the "listed" branch requires an injected fixture -- these
tests build a small, self-contained KEVCatalog rather than touching the live feed or
the real committed data/kev/kev_catalog.json.
"""

from __future__ import annotations

import json

from app.triage import kev


def _fixture_catalog() -> kev.KEVCatalog:
    entries = {
        "CVE-2026-2841": kev.KEVEntry(
            cve_id="CVE-2026-2841",
            date_added="2026-01-01",
            vendor_project="Rockwell Automation",
            product="Allen-Bradley PLC",
            known_ransomware_use="Unknown",
        )
    }
    return kev.KEVCatalog(entries=entries, date_released="2026-01-01T00:00:00Z")


def test_lookup_listed():
    assert kev.lookup(_fixture_catalog(), "CVE-2026-2841") == "listed"


def test_lookup_case_insensitive():
    assert kev.lookup(_fixture_catalog(), "cve-2026-2841") == "listed"


def test_lookup_not_listed():
    assert kev.lookup(_fixture_catalog(), "CVE-1999-0001") == "not_listed"


def test_lookup_unknown_when_no_catalog_data_at_all():
    empty = kev.KEVCatalog(entries={}, date_released=None)
    assert kev.lookup(empty, "CVE-2026-2841") == "unknown"


def test_fetch_and_cache_trims_to_needed_fields(tmp_path, monkeypatch):
    fake_feed = {
        "dateReleased": "2026-01-01T00:00:00Z",
        "vulnerabilities": [
            {
                "cveID": "CVE-2026-2841",
                "vendorProject": "Rockwell Automation",
                "product": "Allen-Bradley PLC",
                "vulnerabilityName": "Test Vuln",
                "dateAdded": "2026-01-01",
                "knownRansomwareCampaignUse": "Known",
                "notes": "irrelevant, should be dropped",
            }
        ],
    }

    class _FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return fake_feed

    monkeypatch.setattr("requests.get", lambda *a, **k: _FakeResponse())

    cache_path = tmp_path / "kev_catalog.json"
    entries, date_released = kev.fetch_and_cache(cache_path=cache_path, url="http://fake")

    assert date_released == "2026-01-01T00:00:00Z"
    assert entries[0].cve_id == "CVE-2026-2841"
    assert entries[0].known_ransomware_use == "Known"

    # Cached file round-trips correctly.
    loaded_entries, loaded_date = kev.load_cached(cache_path)
    assert loaded_date == date_released
    assert loaded_entries == entries

    # Only the trimmed fields are persisted -- not the full upstream record.
    on_disk = json.loads(cache_path.read_text(encoding="utf-8"))
    assert "notes" not in on_disk["entries"][0]
    assert "vulnerabilityName" not in on_disk["entries"][0]


def test_load_cached_missing_file_returns_none(tmp_path):
    assert kev.load_cached(tmp_path / "does_not_exist.json") is None
