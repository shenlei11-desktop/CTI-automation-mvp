"""The severity cascade: pure, no I/O, fully traceable.

Base severity band comes from the official FIRST.org CVSS v3.x qualitative scale (not
an invented mapping -- the defensible choice for a portfolio writeup: "we didn't
invent this part"). Each subsequent factor moves the band up/down one step on an
ordinal ladder rather than multiplying the numeric score: a sentence like "escalated
from Medium to High because the interface is internet-facing" is directly auditable;
"score went from 6.4 to 7.68 via a 1.2x multiplier" is not, despite the extra decimal
looking more precise. Every step -- including no-ops -- emits a :class:`RuleTrace`
entry, so the cascade is always fully visible.

The final severity label always stays one of the 4 clean bands; "unknown" never becomes
a 5th value. Uncertainty about inputs (no CVSS found, exposure/asset-tier unspecified)
lives in the trace and in :func:`assess_clarification_need`, not in the label itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.triage.kev import KEVStatus

_BAND_ORDER = ["Low", "Medium", "High", "Critical"]


@dataclass
class RuleTraceEntry:
    rule: str
    detail: str
    resulting_band: str


@dataclass
class CascadeResult:
    severity: str
    rule_trace: list[RuleTraceEntry]


def cvss_to_band(score: float | None) -> tuple[str, bool]:
    """Official FIRST.org CVSS v3.x qualitative severity scale. Returns
    (band, was_cvss_found) -- absence gets a documented neutral default, not a guess."""
    if score is None:
        return "Medium", False
    if score >= 9.0:
        return "Critical", True
    if score >= 7.0:
        return "High", True
    if score >= 4.0:
        return "Medium", True
    return "Low", True


def _escalate(band: str, steps: int) -> str:
    index = _BAND_ORDER.index(band) + steps
    return _BAND_ORDER[max(0, min(index, len(_BAND_ORDER) - 1))]


def _floor_at(band: str, minimum: str) -> str:
    return band if _BAND_ORDER.index(band) >= _BAND_ORDER.index(minimum) else minimum


def score_finding(
    cvss_score: float | None,
    exposure: str,  # "internet_facing" | "segmented" | "unknown"
    asset_tier: str,  # "safety_critical" | "process_critical" | "monitoring_only" | "unknown"
    kev_status: KEVStatus,
) -> CascadeResult:
    """Run the full cascade for one CVE (or a whole-report finding with no CVE at
    all, in which case ``cvss_score`` is None). Rule application order: CVSS base,
    then exposure, then asset criticality, then KEV last as a floor/override.
    """
    trace: list[RuleTraceEntry] = []

    band, cvss_found = cvss_to_band(cvss_score)
    if cvss_found:
        trace.append(
            RuleTraceEntry(
                "cvss_base",
                f"CVSS score {cvss_score:.1f} maps to base band {band}.",
                band,
            )
        )
    else:
        trace.append(
            RuleTraceEntry(
                "cvss_base",
                "No CVSS score found in report text; defaulted to Medium as a neutral "
                "starting point (not a guess at actual severity).",
                band,
            )
        )

    if exposure == "internet_facing":
        band = _escalate(band, +1)
        trace.append(
            RuleTraceEntry("exposure", "Internet-facing: escalated one band.", band)
        )
    elif exposure == "segmented":
        band = _escalate(band, -1)
        trace.append(
            RuleTraceEntry("exposure", "Segmented/air-gapped: de-escalated one band.", band)
        )
    else:
        trace.append(
            RuleTraceEntry(
                "exposure", "Exposure not specified in report text; no adjustment applied.", band
            )
        )

    if asset_tier == "safety_critical":
        band = _escalate(band, +1)
        trace.append(
            RuleTraceEntry("asset_tier", "Safety-critical asset: escalated one band.", band)
        )
    elif asset_tier == "monitoring_only":
        band = _escalate(band, -1)
        trace.append(
            RuleTraceEntry("asset_tier", "Monitoring-only asset: de-escalated one band.", band)
        )
    else:
        detail = (
            "Process-critical asset: no adjustment applied (neutral tier)."
            if asset_tier == "process_critical"
            else "Asset-criticality tier not specified in report text; no adjustment applied."
        )
        trace.append(RuleTraceEntry("asset_tier", detail, band))

    if kev_status == "listed":
        pre_floor = _escalate(band, +1)
        band = _floor_at(pre_floor, "High")
        trace.append(
            RuleTraceEntry(
                "kev",
                "Listed in CISA's Known Exploited Vulnerabilities catalog: escalated "
                "one band and floored at High regardless of other factors.",
                band,
            )
        )
    else:
        reason = "not confirmed exploited" if kev_status == "not_listed" else "KEV status unknown"
        trace.append(RuleTraceEntry("kev", f"{reason}; no adjustment applied.", band))

    return CascadeResult(severity=band, rule_trace=trace)


def assess_clarification_need(exposure: str, asset_tier: str) -> tuple[bool, str]:
    """The core agentic gate. Deliberately does NOT trigger on missing CVSS -- that
    gets a documented neutral default instead. Only exposure/asset-tier ambiguity
    routes to a human, per the brief's literal wording."""
    missing = []
    if exposure == "unknown":
        missing.append("exposure level")
    if asset_tier == "unknown":
        missing.append("asset-criticality tier")

    if not missing:
        return False, (
            "Exposure and asset-criticality tier were both specified in the report "
            "text; scored with full confidence."
        )

    factors = " and ".join(missing)
    return True, (
        f"{factors.capitalize()} not clearly specified in the report text. Severity "
        "was scored provisionally using neutral defaults for the unspecified "
        "factor(s) -- confirm before acting on this score."
    )
