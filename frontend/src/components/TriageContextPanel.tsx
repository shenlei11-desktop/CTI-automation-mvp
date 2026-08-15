import type { TriageResponse } from "../api/types"

export default function TriageContextPanel({ triage }: { triage: TriageResponse }) {
  const { context, quality } = triage
  return (
    <div className="mb-4 space-y-1.5 font-mono text-xs text-stone-500">
      <div title={context.exposure_source?.sentence}>
        exposure: <span className="text-stone-300">{context.exposure}</span>
        {context.exposure_source && <span className="text-stone-700"> (from report text)</span>}
      </div>
      <div title={context.asset_tier_source?.sentence}>
        asset_tier: <span className="text-stone-300">{context.asset_tier}</span>
        {context.asset_tier_source && <span className="text-stone-700"> (from report text)</span>}
      </div>
      <div className={quality.decision === "scored" ? "text-emerald-500" : "text-amber-500"}>
        {quality.decision}: <span className="text-stone-500">{quality.reason}</span>
      </div>
    </div>
  )
}
