import type { ExtractResponse } from "../api/types"
import { recommendationTextClasses } from "../lib/style"

export default function IOCTable({ extraction }: { extraction: ExtractResponse }) {
  const q = extraction.quality
  return (
    <div>
      <p className="mb-4 font-mono text-xs text-stone-500">
        {q.n_iocs} iocs · {q.n_entities} entities · {q.text_length} chars · signal density{" "}
        {q.signal_density.toFixed(2)}/1k ·{" "}
        <span className={recommendationTextClasses(q.recommendation)}>{q.recommendation}</span>
        <br />
        <span className="text-stone-600">{q.reason}</span>
      </p>
      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <h4 className="mb-2 font-mono text-xs tracking-wide text-stone-500 uppercase">
            IOCs ({extraction.iocs.length})
          </h4>
          {extraction.iocs.length === 0 ? (
            <p className="text-sm text-stone-600">None found.</p>
          ) : (
            <ul className="space-y-1.5">
              {extraction.iocs.map((ioc, i) => (
                <li key={i} className="flex min-w-0 items-start gap-2 text-sm" title={ioc.source.sentence}>
                  <span className="mt-0.5 shrink-0 bg-stone-900 px-1.5 py-0.5 font-mono text-[11px] text-stone-500 uppercase">
                    {ioc.type}
                  </span>
                  <code className="min-w-0 text-stone-300 break-all">{ioc.value_normalized}</code>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4 className="mb-2 font-mono text-xs tracking-wide text-stone-500 uppercase">
            Entities ({extraction.entities.length})
          </h4>
          {extraction.entities.length === 0 ? (
            <p className="text-sm text-stone-600">None found.</p>
          ) : (
            <ul className="space-y-1.5">
              {extraction.entities.map((entity, i) => (
                <li key={i} className="flex min-w-0 items-start gap-2 text-sm" title={entity.source.sentence}>
                  <span className="mt-0.5 shrink-0 bg-stone-900 px-1.5 py-0.5 font-mono text-[11px] text-stone-500 uppercase">
                    {entity.type.replace("_", " ")}
                  </span>
                  <span className="min-w-0 text-stone-300 break-words">{entity.text}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
