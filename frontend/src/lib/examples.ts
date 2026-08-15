export interface DemoExample {
  id: string
  label: string
  description: string
  expectedOutcome: string
  text: string
}

// The first example is the project's bundled data/samples/sample_advisory_01.txt,
// verbatim. The other two are hand-crafted to trigger the pipeline's two "ask a human
// instead of guessing" branches -- both hand-verified against the live backend.
export const EXAMPLES: DemoExample[] = [
  {
    id: "sample-01",
    label: "Fully scored — Critical",
    description:
      "A CISA-style ICS advisory: internet-facing PLC, safety-critical process, CVSS 9.8.",
    expectedOutcome: "completed → Critical severity",
    text: `ICS Advisory (SYNTHETIC SAMPLE) - ICSA-26-XXX-01
Schneider Electric Modicon PLC - Improper Authentication

SUMMARY
CISA is aware of active exploitation targeting internet-facing Schneider Electric
Modicon programmable logic controllers (PLCs) deployed across the water and wastewater
and electric utility sectors. The activity has been attributed with moderate confidence
to the threat actor VOLTZITE, whose tooling overlaps with previously reported ELECTRUM
activity.

TECHNICAL DETAILS
The vulnerability, tracked as CVE-2026-2841, carries a CVSS v3.1 base score of 9.8.
Successful exploitation allows an unauthenticated remote attacker to bypass
authentication and issue unauthorized commands to safety-critical process controllers.

Analysts observed the actor staging payloads from the command-and-control domain
hxxps://update-modicon[.]net and beaconing to 185[.]220[.]101[.]45 over port 443. A
malicious firmware implant was recovered with SHA-256 hash
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855. Some victims also
reported lateral movement to 10[.]0[.]0[.]5 on the internal historian network.

AFFECTED PRODUCTS
Schneider Electric Modicon M340 and M580 controllers (firmware prior to v3.2) are
affected. Rockwell Automation ControlLogix devices were assessed but not confirmed
vulnerable.

MITIGATIONS
Operators should remove PLC management interfaces from direct internet exposure, segment
operational technology networks, and apply vendor firmware v3.2 when available. CISA has
added CVE-2026-2841 to its Known Exploited Vulnerabilities (KEV) catalog.`,
  },
  {
    id: "demo-clarify",
    label: "Needs clarification",
    description: "A CVSS score is given, but nothing about exposure or asset criticality.",
    expectedOutcome: "needs_clarification → provisional High severity, never guessed",
    text: "A vulnerability tracked as CVE-2026-9999 has a CVSS v3.1 base score of 8.1. Organizations should apply the vendor patch as soon as possible. This advisory provides general guidance for affected deployments without further detail about the environment or the specific device roles involved, since no additional context was available at the time of writing this report to any recipients.",
  },
  {
    id: "demo-stub",
    label: "Needs extraction review",
    description: "Too short and low-signal to trust — the hard stop before classification/triage.",
    expectedOutcome: "needs_extraction_review → classification & triage never run",
    text: "too short",
  },
]
