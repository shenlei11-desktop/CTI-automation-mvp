import type { ExtractResponse } from "../api/types"

export default function IOCTable({ extraction }: { extraction: ExtractResponse }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-300">
          IOCs ({extraction.iocs.length})
        </h4>
        {extraction.iocs.length === 0 ? (
          <p className="text-sm text-slate-500">None found.</p>
        ) : (
          <ul className="space-y-1.5">
            {extraction.iocs.map((ioc, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs uppercase text-slate-400">
                  {ioc.type}
                </span>
                <code className="text-slate-300">{ioc.value_normalized}</code>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="mb-2 text-sm font-semibold text-slate-300">
          Entities ({extraction.entities.length})
        </h4>
        {extraction.entities.length === 0 ? (
          <p className="text-sm text-slate-500">None found.</p>
        ) : (
          <ul className="space-y-1.5">
            {extraction.entities.map((entity, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs uppercase text-slate-400">
                  {entity.type.replace("_", " ")}
                </span>
                <span className="text-slate-300">{entity.text}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
