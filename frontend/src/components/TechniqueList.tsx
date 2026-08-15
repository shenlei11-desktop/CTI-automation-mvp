import type { ClassifyResponse } from "../api/types"
import { recommendationClasses } from "../lib/style"

export default function TechniqueList({ classification }: { classification: ClassifyResponse }) {
  const withMatches = classification.behaviors.filter((b) => b.matches.length > 0)

  if (withMatches.length === 0) {
    return <p className="text-sm text-slate-500">No behaviours were classified.</p>
  }

  return (
    <div className="space-y-3">
      {withMatches.map((behavior, i) => (
        <div key={i} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
          <p className="mb-2 line-clamp-2 text-sm text-slate-400">{behavior.text}</p>
          <div className="mb-2 flex flex-wrap gap-2">
            {behavior.matches.slice(0, 3).map((match) => (
              <span
                key={match.technique_id}
                className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300"
              >
                <span className="font-mono text-teal-400">{match.technique_id}</span>{" "}
                {match.technique_name}
              </span>
            ))}
          </div>
          <span
            className={`inline-block rounded border px-2 py-0.5 text-xs ${recommendationClasses(behavior.quality.recommendation)}`}
          >
            {behavior.quality.recommendation === "proceed" ? "Confident" : "Low confidence"}
          </span>
        </div>
      ))}
    </div>
  )
}
