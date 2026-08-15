import type { AdvisoryStatus } from "../api/types"
import { statusClasses } from "../lib/style"

const LABELS: Record<AdvisoryStatus, string> = {
  completed: "Completed",
  needs_extraction_review: "Needs Extraction Review",
  needs_clarification: "Needs Clarification",
}

export default function StatusBadge({ status }: { status: AdvisoryStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${statusClasses(status)}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {LABELS[status]}
    </span>
  )
}
