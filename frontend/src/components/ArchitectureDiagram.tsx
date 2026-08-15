interface Branch {
  title: string
  detail: string
  tone: "red" | "amber"
}

interface Stage {
  title: string
  subtitle: string
  branch?: Branch
}

const STAGES: Stage[] = [
  { title: "Ingestion", subtitle: "PDF / HTML / URL → plain text" },
  {
    title: "Extraction",
    subtitle: "IOCs + entities, every fact tied to its source sentence",
    branch: {
      tone: "red",
      title: "flag_for_review → hard stop",
      detail: "Text too short or too low-signal to trust. Classification and triage never run.",
    },
  },
  {
    title: "Classification",
    subtitle: "ATT&CK-for-ICS technique matching (embedding retrieval + cross-encoder rerank)",
  },
  {
    title: "Triage",
    subtitle: "CVSS band × exposure × asset tier × CISA KEV → severity, fully traced",
    branch: {
      tone: "amber",
      title: "needs_clarification → ask, don't guess",
      detail: "Exposure or asset criticality can't be determined. A provisional score is kept, not withheld.",
    },
  },
  { title: "Advisory", subtitle: "Rendered report, structured JSON, and the full agent trace" },
]

const branchClasses = {
  red: { border: "border-red-500/50", bg: "bg-red-500/5", title: "text-red-300" },
  amber: { border: "border-amber-500/50", bg: "bg-amber-500/5", title: "text-amber-300" },
}

export default function ArchitectureDiagram() {
  return (
    <ol className="mx-auto max-w-lg">
      {STAGES.map((stage, i) => (
        <li key={stage.title} className="relative pb-8 last:pb-0">
          {i < STAGES.length - 1 && (
            <span
              aria-hidden="true"
              className="absolute top-10 left-5 -ml-px h-[calc(100%-1rem)] w-0.5 bg-slate-700"
            />
          )}
          <div className="relative flex items-start gap-4">
            <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-teal-500/40 bg-slate-950 text-sm font-bold text-teal-300">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
                <div className="font-semibold text-slate-100">{stage.title}</div>
                <div className="text-sm text-slate-400">{stage.subtitle}</div>
              </div>
              {stage.branch && (
                <div
                  className={`mt-3 ml-2 rounded-lg border-l-4 py-2 pr-3 pl-4 text-sm ${branchClasses[stage.branch.tone].border} ${branchClasses[stage.branch.tone].bg}`}
                >
                  <div className={`font-semibold ${branchClasses[stage.branch.tone].title}`}>
                    {stage.branch.title}
                  </div>
                  <div className="text-slate-400">{stage.branch.detail}</div>
                </div>
              )}
            </div>
          </div>
        </li>
      ))}
    </ol>
  )
}
