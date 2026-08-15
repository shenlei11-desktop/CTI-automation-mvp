import type { AdvisoryStatus } from "../api/types"
import { statusTextClasses } from "../lib/style"

const LABELS: Record<AdvisoryStatus, string> = {
  completed: "completed",
  needs_extraction_review: "needs_extraction_review",
  needs_clarification: "needs_clarification",
}

export default function StatusBadge({ status }: { status: AdvisoryStatus }) {
  return (
    <span className={`inline-flex items-center gap-2 font-mono text-sm ${statusTextClasses(status)}`}>
      <span className="h-1.5 w-1.5 bg-current" />
      {LABELS[status]}
    </span>
  )
}
