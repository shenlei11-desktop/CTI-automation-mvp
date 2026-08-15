"""End-to-end tests for the /triage endpoint.

No spaCy/fastembed model dependency (only regex + spacy.blank sentencizer), so these
run unconditionally -- no skip guard needed.
"""

from __future__ import annotations

from app.triage import kev


def test_triage_sample_advisory_scored_critical(client, sample_text):
    resp = client.post("/triage", json={"text": sample_text, "report_id": "sample-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == "sample-01"
    assert data["quality"]["decision"] == "scored"
    assert data["context"]["exposure"] == "internet_facing"
    assert data["context"]["asset_tier"] == "safety_critical"

    finding = data["findings"][0]
    assert finding["cve_id"] == "CVE-2026-2841"
    assert finding["cvss_score"] == 9.8
    assert finding["severity"] == "Critical"
    # Real KEV feed: this fictional CVE genuinely isn't listed -- the system verifies
    # independently rather than trusting the report text's own KEV claim.
    assert finding["kev_status"] == "not_listed"

    # Full cascade visible, including no-op steps, each traceable to its evidence.
    rules = [t["rule"] for t in finding["rule_trace"]]
    assert rules == ["cvss_base", "exposure", "asset_tier", "kev"]
    assert finding["rule_trace"][0]["source"]["sentence"].strip() != ""


def test_triage_needs_clarification_when_exposure_and_tier_unspecified(client):
    resp = client.post(
        "/triage",
        json={
            "text": (
                "A vulnerability tracked as CVE-2026-9999 has a CVSS v3.1 base score "
                "of 8.1. Organizations should apply the vendor patch as soon as possible."
            )
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quality"]["decision"] == "needs_clarification"
    assert data["context"]["exposure"] == "unknown"
    assert data["context"]["asset_tier"] == "unknown"
    # A provisional score is still returned -- never withheld.
    assert data["findings"][0]["severity"] == "High"


def test_triage_no_cve_found(client):
    resp = client.post(
        "/triage", json={"text": "The vendor released a general advisory with no details."}
    )
    assert resp.status_code == 200
    finding = resp.json()["findings"][0]
    assert finding["cve_id"] is None
    assert finding["severity"] == "Medium"


def test_triage_kev_listed_floors_severity_at_high(client, monkeypatch):
    # Injected fixture: the real feed can never contain this scenario's CVE, so the
    # "listed" branch is tested via a monkeypatched catalog, not live data.
    fixture_catalog = kev.KEVCatalog(
        entries={
            "CVE-2026-0001": kev.KEVEntry(
                cve_id="CVE-2026-0001",
                date_added="2026-01-01",
                vendor_project="Test Vendor",
                product="Test Product",
                known_ransomware_use="Unknown",
            )
        },
        date_released="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr(kev, "get_kev_catalog", lambda: fixture_catalog)

    resp = client.post(
        "/triage",
        json={
            "text": (
                "CVE-2026-0001 has a CVSS score of 2.0. The device is air-gapped and "
                "used only for monitoring only."
            )
        },
    )
    assert resp.status_code == 200
    finding = resp.json()["findings"][0]
    # Low base (2.0) + segmented (-1) + monitoring-only (-1) would bottom out at Low,
    # but KEV-listed floors the result at High regardless of the other de-escalations.
    assert finding["kev_status"] == "listed"
    assert finding["severity"] == "High"


def test_triage_empty_text_rejected(client):
    resp = client.post("/triage", json={"text": ""})
    assert resp.status_code == 422
