"""Unit tests for triage signal detection (pure regex/keyword matching, no models)."""

from __future__ import annotations

from app.extraction import ioc, provenance
from app.triage import signals


def test_detect_cvss_mentions_various_phrasings():
    assert [m.score for m in signals.detect_cvss_mentions("CVSS v3.1 base score of 9.8")] == [9.8]
    assert [m.score for m in signals.detect_cvss_mentions("CVSS score: 7.5")] == [7.5]
    assert [m.score for m in signals.detect_cvss_mentions("CVSS 9.8")] == [9.8]


def test_detect_cvss_mentions_rejects_out_of_range():
    # A malformed "CVSS 42" should not be captured as a valid 0-10 score.
    assert signals.detect_cvss_mentions("CVSS 42") == []


def test_detect_exposure_signals_and_resolve_single_category():
    hits = signals.detect_exposure_signals("The interface is internet-facing.")
    resolved, hit = signals.resolve_exposure(hits)
    assert resolved == "internet_facing"
    assert hit.phrase == "internet-facing"


def test_resolve_exposure_no_hits_is_unknown():
    resolved, hit = signals.resolve_exposure([])
    assert resolved == "unknown"
    assert hit is None


def test_resolve_exposure_both_categories_is_unknown():
    # Genuine ambiguity: current-state claim + a recommendation can't be
    # disambiguated by keyword matching alone -- unknown is the safer failure mode.
    text = "The interface is internet-facing. Operators should implement network segmentation."
    hits = signals.detect_exposure_signals(text)
    resolved, hit = signals.resolve_exposure(hits)
    assert resolved == "unknown"
    assert hit is None


def test_resolve_asset_tier_safety_critical_not_confused_by_process_controller():
    # Regression: "safety-critical process controllers" must resolve cleanly to
    # safety_critical, not "unknown" via an accidental process_critical collision.
    hits = signals.detect_asset_tier_signals(
        "unauthorized commands to safety-critical process controllers"
    )
    resolved, hit = signals.resolve_asset_tier(hits)
    assert resolved == "safety_critical"


def test_associate_cvss_to_cves_single_cve_single_mention():
    text = "The vulnerability, tracked as CVE-2026-2841, has a CVSS score of 9.8."
    cve_iocs = [r for r in ioc.extract_iocs(text) if r.type == "cve"]
    cvss = signals.detect_cvss_mentions(text)
    sentences = provenance.build_sentence_index(text)
    result = signals.associate_cvss_to_cves(cve_iocs, cvss, sentences)
    assert result["CVE-2026-2841"].score == 9.8


def test_associate_cvss_to_cves_no_cve_no_association():
    result = signals.associate_cvss_to_cves([], [], [])
    assert result == {}


def test_associate_cvss_to_cves_multiple_cves_unpaired_without_same_sentence():
    # Two CVEs (so the exactly-one-and-one fast path doesn't apply) and a CVSS
    # mention that shares a sentence with neither -> both stay unassociated rather
    # than guessing which CVE it belongs to.
    text = (
        "CVE-2026-0001 was found. Separately, CVE-2026-0002 was also found. "
        "A CVSS score of 5.0 was assigned overall."
    )
    cve_iocs = [r for r in ioc.extract_iocs(text) if r.type == "cve"]
    cvss = signals.detect_cvss_mentions(text)
    sentences = provenance.build_sentence_index(text)
    result = signals.associate_cvss_to_cves(cve_iocs, cvss, sentences)
    assert len(cve_iocs) == 2 and len(cvss) == 1
    assert all(v is None for v in result.values())
