import type { TechniqueRollup } from "../api/types"

const MARGIN_THRESHOLD = 1.25
const MARGIN_SCALE_MAX = 4 // median correct-prediction margin was 2.35; this gives headroom

function MarginBar({ margin }: { margin: number | null }) {
  if (margin === null) return <span className="font-mono text-xs text-stone-600">no runner-up</span>
  const pct = Math.min(100, (margin / MARGIN_SCALE_MAX) * 100)
  const thresholdPct = (MARGIN_THRESHOLD / MARGIN_SCALE_MAX) * 100
  const confident = margin >= MARGIN_THRESHOLD
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 w-28 bg-stone-800">
        <div
          className={`absolute inset-y-0 left-0 ${confident ? "bg-emerald-500" : "bg-amber-500"}`}
          style={{ width: `${pct}%` }}
        />
        <div className="absolute inset-y-0 w-px bg-stone-400" style={{ left: `${thresholdPct}%` }} />
      </div>
      <span className="font-mono text-xs text-stone-500">margin {margin.toFixed(2)}</span>
    </div>
  )
}

export default function TechniqueList({ techniques }: { techniques: TechniqueRollup[] }) {
  if (techniques.length === 0) {
    return <p className="font-mono text-sm text-stone-500">No techniques observed in this report.</p>
  }

  return (
    <div className="divide-y divide-stone-800 border-y border-stone-800">
      {techniques.map((t) => (
        <div key={t.technique_id} className="py-4">
          <div className="mb-1.5 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <a
              href={t.attack_url}
              target="_blank"
              rel="noreferrer"
              className="font-serif text-base font-semibold text-stone-100 hover:text-amber-400"
            >
              <span className="font-mono text-sm text-amber-500">{t.technique_id}</span> {t.technique_name}
            </a>
            <MarginBar margin={t.best_margin} />
          </div>

          <div className="mb-2 flex flex-wrap gap-1.5">
            {t.tactics.map((tactic) => (
              <span key={tactic} className="bg-stone-900 px-1.5 py-0.5 font-mono text-[11px] text-stone-500">
                {tactic}
              </span>
            ))}
            <span
              className={`px-1.5 py-0.5 font-mono text-[11px] ${
                t.recommendation === "proceed" ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              {t.recommendation}
            </span>
          </div>

          <ul className="mb-2 space-y-1">
            {t.evidence.map((e, i) => (
              <li key={i} className="border-l-2 border-stone-800 pl-3 text-sm text-stone-400 italic">
                "{e.text.trim()}"
              </li>
            ))}
          </ul>

          {t.mitigation && (
            <details className="text-sm text-stone-500">
              <summary className="cursor-pointer font-mono text-xs text-stone-600 hover:text-stone-400">
                mitigation
              </summary>
              <p className="mt-1.5 leading-relaxed">{t.mitigation}</p>
            </details>
          )}
        </div>
      ))}
    </div>
  )
}
