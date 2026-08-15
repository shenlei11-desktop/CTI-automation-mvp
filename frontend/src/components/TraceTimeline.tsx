import type { TraceEntry } from "../api/types"

const NODE_LABELS: Record<string, string> = {
  extraction: "extraction",
  classification: "classification",
  triage: "triage",
  finalize: "finalize",
  needs_extraction_review: "needs_extraction_review",
  needs_clarification: "needs_clarification",
}

export default function TraceTimeline({ trace }: { trace: TraceEntry[] }) {
  return (
    <ol className="space-y-1.5 font-mono text-xs">
      {trace.map((entry, i) => (
        <li key={i} className="flex gap-3 text-stone-500">
          <span className="text-stone-700">{String(i + 1).padStart(2, "0")}</span>
          <span className="text-amber-500">{NODE_LABELS[entry.node] ?? entry.node}</span>
          <span className="text-stone-600">{entry.detail}</span>
        </li>
      ))}
    </ol>
  )
}
