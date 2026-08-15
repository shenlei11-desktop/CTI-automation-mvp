"""Unit tests for the severity cascade (pure logic, no I/O, no models)."""

from __future__ import annotations

from app.triage import cascade


def test_cvss_to_band_official_scale():
    assert cascade.cvss_to_band(9.8) == ("Critical", True)
    assert cascade.cvss_to_band(9.0) == ("Critical", True)
    assert cascade.cvss_to_band(8.9) == ("High", True)
    assert cascade.cvss_to_band(7.0) == ("High", True)
    assert cascade.cvss_to_band(6.9) == ("Medium", True)
    assert cascade.cvss_to_band(4.0) == ("Medium", True)
    assert cascade.cvss_to_band(3.9) == ("Low", True)
    assert cascade.cvss_to_band(0.1) == ("Low", True)


def test_cvss_to_band_missing_defaults_to_medium():
    assert cascade.cvss_to_band(None) == ("Medium", False)


def test_score_finding_critical_stays_clamped_at_ceiling():
    result = cascade.score_finding(9.8, "internet_facing", "safety_critical", "not_listed")
    assert result.severity == "Critical"
    assert [t.rule for t in result.rule_trace] == ["cvss_base", "exposure", "asset_tier", "kev"]


def test_score_finding_all_neutral_stays_medium():
    result = cascade.score_finding(None, "unknown", "unknown", "not_listed")
    assert result.severity == "Medium"
    # No-op steps still emit a trace entry -- the cascade is always fully visible.
    assert len(result.rule_trace) == 4


def test_score_finding_kev_floors_at_high_overriding_deescalations():
    # Low base, de-escalated twice (segmented, monitoring-only) would reach the floor
    # of the ladder -- but KEV-listed floors the result at High regardless.
    result = cascade.score_finding(2.0, "segmented", "monitoring_only", "listed")
    assert result.severity == "High"


def test_score_finding_kev_escalates_without_floor_effect_when_already_high():
    result = cascade.score_finding(7.5, "unknown", "unknown", "listed")
    # High base -> KEV +1 -> Critical (no floor needed, already above High)
    assert result.severity == "Critical"


def test_score_finding_exposure_and_asset_tier_escalate_independently():
    result = cascade.score_finding(5.0, "internet_facing", "process_critical", "not_listed")
    # Medium base +1 (internet-facing) +0 (process-critical is neutral) = High
    assert result.severity == "High"


def test_assess_clarification_need_both_specified():
    needs_clarification, reason = cascade.assess_clarification_need(
        "internet_facing", "safety_critical"
    )
    assert needs_clarification is False
    assert "scored with full confidence" in reason


def test_assess_clarification_need_missing_exposure_only():
    needs_clarification, reason = cascade.assess_clarification_need("unknown", "safety_critical")
    assert needs_clarification is True
    assert "Exposure level" in reason
    assert "asset-criticality" not in reason.lower()


def test_assess_clarification_need_does_not_trigger_on_missing_cvss():
    # By design: missing CVSS gets a documented neutral default, not a clarification
    # request -- only exposure/asset-tier ambiguity triggers the agentic gate.
    result = cascade.score_finding(None, "internet_facing", "safety_critical", "not_listed")
    needs_clarification, _ = cascade.assess_clarification_need("internet_facing", "safety_critical")
    assert result.severity is not None  # a provisional score was still produced
    assert needs_clarification is False
