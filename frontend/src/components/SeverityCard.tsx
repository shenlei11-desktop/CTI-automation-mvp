import type { CVEFinding } from "../api/types"
import { severityBorderClasses, severityTextClasses } from "../lib/style"

export default function SeverityCard({ finding }: { finding: CVEFinding }) {
  return (
    <div className={`border-l-2 ${severityBorderClasses(finding.severity)} pl-4`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <div className="font-mono text-sm text-stone-200">{finding.cve_id ?? "No CVE cited"}</div>
          {finding.cvss_score != null && (
            <div className="font-mono text-xs text-stone-500">CVSS {finding.cvss_score.toFixed(1)}</div>
          )}
        </div>
        <span className={`shrink-0 font-serif text-lg font-semibold ${severityTextClasses(finding.severity)}`}>
          {finding.severity}
        </span>
      </div>
      <div className="mb-2 font-mono text-xs text-stone-500">
        KEV: <span className="text-stone-300">{finding.kev_status.replace("_", " ")}</span>
      </div>
      <ol className="space-y-1">
        {finding.rule_trace.map((step, i) => (
          <li key={i} className="text-sm text-stone-400">
            <span className="font-mono text-xs text-amber-500">{step.rule}</span> — {step.detail}
          </li>
        ))}
      </ol>
    </div>
  )
}
