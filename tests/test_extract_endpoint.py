"""End-to-end tests for the /extract endpoint (requires en_core_web_sm)."""

from __future__ import annotations

import pytest

from tests.conftest import MODEL_AVAILABLE

pytestmark = pytest.mark.skipif(
    not MODEL_AVAILABLE, reason="spaCy model en_core_web_sm not installed"
)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_extract_sample_advisory(client, sample_text):
    resp = client.post("/extract", json={"text": sample_text, "report_id": "sample-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == "sample-01"

    ioc_norms = {(i["type"], i["value_normalized"]) for i in data["iocs"]}
    assert ("domain", "update-modicon.net") in ioc_norms
    assert ("ipv4", "185.220.101.45") in ioc_norms
    assert ("cve", "CVE-2026-2841") in ioc_norms
    assert (
        "sha256",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ) in ioc_norms

    # The internal historian IP is private and must be tagged as such.
    private = [i for i in data["iocs"] if i["value_normalized"] == "10.0.0.5"]
    assert private and private[0]["is_private"] is True

    ent_pairs = {(e["type"], e["text"]) for e in data["entities"]}
    assert ("threat_actor", "VOLTZITE") in ent_pairs
    assert ("ics_vendor", "Schneider Electric") in ent_pairs

    # Technical acronyms/labels that general-purpose NER mislabels as orgs are suppressed.
    ent_texts = {e["text"] for e in data["entities"]}
    assert "CVSS" not in ent_texts
    assert "KEV" not in ent_texts
    assert "ICS Advisory" not in ent_texts
    # A partial CVE ("CVE-2026") must not leak through as a generic organization.
    assert "CVE-2026" not in ent_texts

    # Provenance: every extracted fact traces back to a non-empty source sentence.
    for item in data["iocs"] + data["entities"]:
        assert item["source"]["sentence"].strip() != ""

    assert data["quality"]["recommendation"] == "proceed"


def test_short_text_flagged_for_review(client):
    resp = client.post("/extract", json={"text": "Nothing to see."})
    assert resp.status_code == 200
    assert resp.json()["quality"]["recommendation"] == "flag_for_review"


def test_empty_text_rejected(client):
    resp = client.post("/extract", json={"text": ""})
    assert resp.status_code == 422
