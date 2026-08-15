import type { AdvisoryStatus, Recommendation, SeverityBand } from "../api/types"

export function severityTextClasses(band: SeverityBand): string {
  switch (band) {
    case "Critical":
      return "text-red-400"
    case "High":
      return "text-orange-400"
    case "Medium":
      return "text-amber-400"
    case "Low":
      return "text-emerald-400"
  }
}

export function severityBorderClasses(band: SeverityBand): string {
  switch (band) {
    case "Critical":
      return "border-red-500/50"
    case "High":
      return "border-orange-500/50"
    case "Medium":
      return "border-amber-500/50"
    case "Low":
      return "border-emerald-500/50"
  }
}

export function statusTextClasses(status: AdvisoryStatus): string {
  switch (status) {
    case "completed":
      return "text-emerald-400"
    case "needs_extraction_review":
      return "text-red-400"
    case "needs_clarification":
      return "text-amber-400"
  }
}

export function recommendationTextClasses(recommendation: Recommendation): string {
  return recommendation === "proceed" ? "text-emerald-400" : "text-amber-400"
}
