"""Pydantic models for the triage stage.

Defines the public API contract for ``POST /triage``. The severity cascade is fully
traceable: every :class:`CVEFinding` carries the ``rule_trace`` that produced its
``severity``, satisfying "every severity score shows exactly which rule produced it."
``findings`` is a list because a report may cite several CVEs, each scored
independently; exposure/asset-criticality are properties of the deployment as a whole
and are computed once per report in :class:`TriageContext`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.extraction import SourceSpan

KEVStatus = Literal["listed", "not_listed", "unknown"]
ExposureLevel = Literal["internet_facing", "segmented", "unknown"]
AssetTier = Literal["safety_critical", "process_critical", "monitoring_only", "unknown"]
SeverityBand = Literal["Critical", "High", "Medium", "Low"]
TriageDecision = Literal["scored", "needs_clarification"]


class RuleTrace(BaseModel):
    """One step of the severity cascade."""

    rule: str = Field(..., description="Which rule fired: cvss_base, exposure, asset_tier, kev.")
    detail: str = Field(..., description="Human-readable explanation of this step's effect.")
    resulting_band: SeverityBand = Field(..., description="Severity band after this step.")
    source: SourceSpan | None = Field(
        None, description="Where this step's evidence was found, if any (no-op steps have none)."
    )


class CVEFinding(BaseModel):
    """Severity assessment for one CVE (or the whole report, if no CVE was found)."""

    cve_id: str | None = None
    cvss_score: float | None = None
    kev_status: KEVStatus
    severity: SeverityBand
    rule_trace: list[RuleTrace]
    source: SourceSpan | None = None


class TriageContext(BaseModel):
    """Report-level factors shared by every finding."""

    exposure: ExposureLevel
    exposure_source: SourceSpan | None = None
    asset_tier: AssetTier
    asset_tier_source: SourceSpan | None = None


class TriageQuality(BaseModel):
    """The core agentic decision: score confidently, or ask a human.

    Deliberately does not trigger on missing CVSS (that gets a documented neutral
    default instead) -- only on exposure/asset-tier ambiguity, per the project brief.
    """

    decision: TriageDecision
    reason: str = Field(..., description="Human-readable justification for the decision.")


class TriageRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw report text to triage.")
    report_id: str | None = Field(
        None, description="Optional caller-supplied identifier, echoed back in the response."
    )


class TriageResponse(BaseModel):
    report_id: str | None = None
    context: TriageContext
    findings: list[CVEFinding]
    quality: TriageQuality
