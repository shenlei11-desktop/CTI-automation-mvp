"""Renders the human-readable half of the advisory from a finished :class:`AdvisoryState`.

The JSON response (:class:`AdvisoryResponse`) is the machine-readable half; this is the
plain-language summary a human analyst reads first.
"""

from __future__ import annotations

from app.orchestration.state import AdvisoryState

_STATUS_CAVEATS = {
    "needs_extraction_review": (
        "** Flagged for manual review before proceeding. Extraction did not trust this "
        "input enough to run classification or triage automatically. **"
    ),
    "needs_clarification": (
        "** Needs analyst input: exposure and/or asset-criticality could not be "
        "determined from the report text. The severity below is provisional. **"
    ),
}


def render(state: AdvisoryState) -> str:
    lines: list[str] = [f"Advisory for report: {state.report_id or '(no id)'}"]

    caveat = _STATUS_CAVEATS.get(state.status)
    if caveat:
        lines.append(caveat)

    if state.classification is not None:
        lines.append("")
        lines.append("ATT&CK-for-ICS techniques observed:")
        for technique in state.classification.techniques:
            lines.append(
                f"  - {technique.technique_id} {technique.technique_name} "
                f"(rerank score {technique.best_rerank_score:.2f}, {technique.recommendation}, "
                f"{len(technique.evidence)} supporting sentence(s))"
            )

    if state.triage is not None:
        lines.append("")
        lines.append(
            f"Severity (exposure: {state.triage.context.exposure}, "
            f"asset tier: {state.triage.context.asset_tier}):"
        )
        for finding in state.triage.findings:
            cve = finding.cve_id or "(no CVE cited)"
            lines.append(f"  - {cve}: {finding.severity} (KEV: {finding.kev_status})")
            for step in finding.rule_trace:
                lines.append(f"      * {step.rule}: {step.detail}")

    lines.append("")
    lines.append(f"Status: {state.status}")
    return "\n".join(lines)
