import { useState, type FormEvent } from "react"

export type InputMode = "text" | "html" | "url" | "pdf"

interface Props {
  onSubmit: (mode: InputMode, value: string | File) => void
  disabled: boolean
}

const MODES: { id: InputMode; label: string }[] = [
  { id: "text", label: "Paste text" },
  { id: "html", label: "Paste HTML" },
  { id: "url", label: "Fetch URL" },
  { id: "pdf", label: "Upload PDF" },
]

export default function InputPanel({ onSubmit, disabled }: Props) {
  const [mode, setMode] = useState<InputMode>("text")
  const [text, setText] = useState("")
  const [url, setUrl] = useState("")
  const [file, setFile] = useState<File | null>(null)

  const canSubmit =
    mode === "url" ? url.trim().length > 0 : mode === "pdf" ? file !== null : text.trim().length > 0

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (mode === "url") onSubmit("url", url.trim())
    else if (mode === "pdf" && file) onSubmit("pdf", file)
    else if (mode === "text" || mode === "html") onSubmit(mode, text)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex flex-wrap gap-2 font-mono text-xs uppercase">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={`px-3 py-1.5 transition-colors ${
              mode === m.id
                ? "bg-amber-500/10 text-amber-400"
                : "bg-stone-900 text-stone-500 hover:text-stone-300"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === "url" ? (
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.cisa.gov/news-events/ics-advisories/icsa-..."
          className="w-full border border-stone-800 bg-stone-900 px-3 py-2 font-mono text-sm text-stone-200 placeholder-stone-600 focus:border-amber-500/50 focus:outline-none"
        />
      ) : mode === "pdf" ? (
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full border border-stone-800 bg-stone-900 px-3 py-2 text-sm text-stone-400 file:mr-3 file:border-0 file:bg-amber-500/10 file:px-3 file:py-1 file:text-amber-400"
        />
      ) : (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder={mode === "html" ? "Paste raw HTML..." : "Paste report text..."}
          className="w-full border border-stone-800 bg-stone-900 px-3 py-2 font-mono text-sm text-stone-200 placeholder-stone-600 focus:border-amber-500/50 focus:outline-none"
        />
      )}

      <button
        type="submit"
        disabled={disabled || !canSubmit}
        className="border border-amber-500 px-5 py-2 font-mono text-sm font-medium text-amber-400 transition-colors hover:bg-amber-500 hover:text-stone-950 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {disabled ? "running…" : "run pipeline →"}
      </button>
    </form>
  )
}
