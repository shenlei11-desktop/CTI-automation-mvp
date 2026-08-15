import { EXAMPLES, type DemoExample } from "../lib/examples"

interface Props {
  onSelect: (example: DemoExample) => void
  disabled: boolean
}

export default function ExampleButtons({ onSelect, disabled }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {EXAMPLES.map((example) => (
        <button
          key={example.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(example)}
          className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-left transition-colors hover:border-teal-500/40 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <div className="mb-1 font-medium text-slate-200">{example.label}</div>
          <div className="mb-2 text-sm text-slate-500">{example.description}</div>
          <div className="text-xs text-teal-400">{example.expectedOutcome}</div>
        </button>
      ))}
    </div>
  )
}
