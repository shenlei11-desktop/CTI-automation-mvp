"""Triage service: orchestrates signal detection, KEV lookup, and the severity cascade.

This is the single entry point the API calls. Calls ``ioc.extract_iocs()`` directly
(the raw function, not ``extraction.service.extract()``) since triage only needs CVE
mentions and shouldn't pay for spaCy NER.
"""

from __future__ import annotations

from app.extraction import ioc as ioc_mod
from app.extraction import provenance as prov
from app.schemas.extraction import SourceSpan
from app.schemas.triage import (
    CVEFinding,
    RuleTrace,
    TriageContext,
    TriageQuality,
    TriageResponse,
)
from app.triage import cascade, kev, signals


def _rule_sources(
    cvss_source: SourceSpan | None,
    exposure_source: SourceSpan | None,
    asset_tier_source: SourceSpan | None,
    cve_source: SourceSpan | None,
) -> dict[str, SourceSpan | None]:
    return {
        "cvss_base": cvss_source,
        "exposure": exposure_source,
        "asset_tier": asset_tier_source,
        "kev": cve_source,
    }


def _attach_trace_sources(
    trace_entries: list[cascade.RuleTraceEntry], sources: dict[str, SourceSpan | None]
) -> list[RuleTrace]:
    return [
        RuleTrace(
            rule=entry.rule,
            detail=entry.detail,
            resulting_band=entry.resulting_band,
            source=sources.get(entry.rule),
        )
        for entry in trace_entries
    ]


def triage(text: str, report_id: str | None = None) -> TriageResponse:
    """Run the full triage stage over ``text`` and return a structured response."""
    sentences = prov.build_sentence_index(text)

    raw_iocs = ioc_mod.extract_iocs(text)
    cve_iocs = [r for r in raw_iocs if r.type == "cve"]
    cvss_mentions = signals.detect_cvss_mentions(text)

    exposure_hits = signals.detect_exposure_signals(text)
    exposure, exposure_hit = signals.resolve_exposure(exposure_hits)
    exposure_source = (
        prov.locate(sentences, exposure_hit.start, exposure_hit.end) if exposure_hit else None
    )

    asset_tier_hits = signals.detect_asset_tier_signals(text)
    asset_tier, asset_tier_hit = signals.resolve_asset_tier(asset_tier_hits)
    asset_tier_source = (
        prov.locate(sentences, asset_tier_hit.start, asset_tier_hit.end)
        if asset_tier_hit
        else None
    )

    context = TriageContext(
        exposure=exposure,
        exposure_source=exposure_source,
        asset_tier=asset_tier,
        asset_tier_source=asset_tier_source,
    )

    catalog = kev.get_kev_catalog()
    findings: list[CVEFinding] = []

    if cve_iocs:
        cvss_by_cve = signals.associate_cvss_to_cves(cve_iocs, cvss_mentions, sentences)
        for cve in cve_iocs:
            mention = cvss_by_cve[cve.value_normalized]
            cvss_score = mention.score if mention else None
            kev_status = kev.lookup(catalog, cve.value_normalized)

            result = cascade.score_finding(cvss_score, exposure, asset_tier, kev_status)
            cvss_source = prov.locate(sentences, mention.start, mention.end) if mention else None
            cve_source = prov.locate(sentences, cve.start, cve.end)
            sources = _rule_sources(cvss_source, exposure_source, asset_tier_source, cve_source)

            findings.append(
                CVEFinding(
                    cve_id=cve.value_normalized,
                    cvss_score=cvss_score,
                    kev_status=kev_status,
                    severity=result.severity,
                    rule_trace=_attach_trace_sources(result.rule_trace, sources),
                    source=cve_source,
                )
            )
    else:
        # No CVE named at all: still score once, using a lone CVSS mention if present.
        mention = cvss_mentions[0] if len(cvss_mentions) == 1 else None
        cvss_score = mention.score if mention else None
        kev_status: kev.KEVStatus = "unknown"  # nothing to look up without a CVE

        result = cascade.score_finding(cvss_score, exposure, asset_tier, kev_status)
        cvss_source = prov.locate(sentences, mention.start, mention.end) if mention else None
        sources = _rule_sources(cvss_source, exposure_source, asset_tier_source, None)

        findings.append(
            CVEFinding(
                cve_id=None,
                cvss_score=cvss_score,
                kev_status=kev_status,
                severity=result.severity,
                rule_trace=_attach_trace_sources(result.rule_trace, sources),
                source=None,
            )
        )

    needs_clarification, reason = cascade.assess_clarification_need(exposure, asset_tier)
    quality = TriageQuality(
        decision="needs_clarification" if needs_clarification else "scored", reason=reason
    )

    return TriageResponse(report_id=report_id, context=context, findings=findings, quality=quality)
