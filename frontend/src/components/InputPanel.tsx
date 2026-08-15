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
      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === m.id
                ? "bg-teal-500/15 text-teal-300"
                : "bg-slate-900 text-slate-400 hover:text-slate-200"
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
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-teal-500/50 focus:outline-none"
        />
      ) : mode === "pdf" ? (
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-400 file:mr-3 file:rounded file:border-0 file:bg-teal-500/15 file:px-3 file:py-1 file:text-teal-300"
        />
      ) : (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder={mode === "html" ? "Paste raw HTML..." : "Paste report text..."}
          className="w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-200 placeholder-slate-600 focus:border-teal-500/50 focus:outline-none"
        />
      )}

      <button
        type="submit"
        disabled={disabled || !canSubmit}
        className="rounded-lg bg-teal-500 px-5 py-2 font-semibold text-slate-950 transition-colors hover:bg-teal-400 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {disabled ? "Running…" : "Run pipeline"}
      </button>
    </form>
  )
}
