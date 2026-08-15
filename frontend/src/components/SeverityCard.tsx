import type { CVEFinding } from "../api/types"
import { severityClasses } from "../lib/style"

export default function SeverityCard({ finding }: { finding: CVEFinding }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="font-mono text-sm text-slate-200">{finding.cve_id ?? "No CVE cited"}</div>
          {finding.cvss_score != null && (
            <div className="text-xs text-slate-500">CVSS {finding.cvss_score.toFixed(1)}</div>
          )}
        </div>
        <span
          className={`shrink-0 rounded-full border px-3 py-1 text-sm font-semibold ${severityClasses(finding.severity)}`}
        >
          {finding.severity}
        </span>
      </div>
      <div className="mb-3 text-xs text-slate-500">
        KEV status: <span className="text-slate-300">{finding.kev_status.replace("_", " ")}</span>
      </div>
      <ol className="space-y-1.5 border-t border-slate-800 pt-3">
        {finding.rule_trace.map((step, i) => (
          <li key={i} className="text-sm text-slate-400">
            <span className="font-mono text-xs text-teal-400">{step.rule}</span> — {step.detail}
          </li>
        ))}
      </ol>
    </div>
  )
}
