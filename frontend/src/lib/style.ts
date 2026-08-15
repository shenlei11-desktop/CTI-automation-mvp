import type { AdvisoryStatus, Recommendation, SeverityBand } from "../api/types"

export function severityClasses(band: SeverityBand): string {
  switch (band) {
    case "Critical":
      return "bg-red-500/15 text-red-300 border-red-500/40"
    case "High":
      return "bg-orange-500/15 text-orange-300 border-orange-500/40"
    case "Medium":
      return "bg-amber-500/15 text-amber-300 border-amber-500/40"
    case "Low":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
  }
}

export function statusClasses(status: AdvisoryStatus): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
    case "needs_extraction_review":
      return "bg-red-500/15 text-red-300 border-red-500/40"
    case "needs_clarification":
      return "bg-amber-500/15 text-amber-300 border-amber-500/40"
  }
}

export function recommendationClasses(recommendation: Recommendation): string {
  return recommendation === "proceed"
    ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/40"
    : "bg-amber-500/15 text-amber-300 border-amber-500/40"
}
