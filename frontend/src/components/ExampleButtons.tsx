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
          className="border border-stone-800 bg-stone-900/40 p-4 text-left transition-colors hover:border-amber-500/40 hover:bg-stone-900 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <div className="mb-1 font-medium text-stone-200">{example.label}</div>
          <div className="mb-2 text-sm text-stone-500">{example.description}</div>
          <div className="font-mono text-xs text-amber-500">{example.expectedOutcome}</div>
        </button>
      ))}
    </div>
  )
}
