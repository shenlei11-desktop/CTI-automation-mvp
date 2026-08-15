import type { TraceEntry } from "../api/types"

const NODE_LABELS: Record<string, string> = {
  extraction: "Extraction",
  classification: "Classification",
  triage: "Triage",
  finalize: "Finalize",
  needs_extraction_review: "Needs Extraction Review",
  needs_clarification: "Needs Clarification",
}

export default function TraceTimeline({ trace }: { trace: TraceEntry[] }) {
  return (
    <ol>
      {trace.map((entry, i) => (
        <li key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-teal-500/20 text-xs font-semibold text-teal-300">
              {i + 1}
            </span>
            {i < trace.length - 1 && <span className="w-px flex-1 bg-slate-700" />}
          </div>
          <div className="pb-4">
            <div className="text-sm font-medium text-slate-200">
              {NODE_LABELS[entry.node] ?? entry.node}
            </div>
            <div className="text-sm text-slate-400">{entry.detail}</div>
          </div>
        </li>
      ))}
    </ol>
  )
}
