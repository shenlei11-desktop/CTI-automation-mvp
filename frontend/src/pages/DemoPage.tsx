import { useState } from "react"
import { ApiError, getAdvisory, ingestHtml, ingestPdf, ingestUrl } from "../api/client"
import type { AdvisoryResponse, IngestResponse } from "../api/types"
import ExampleButtons from "../components/ExampleButtons"
import InputPanel, { type InputMode } from "../components/InputPanel"
import IOCTable from "../components/IOCTable"
import SeverityCard from "../components/SeverityCard"
import StatusBadge from "../components/StatusBadge"
import TechniqueList from "../components/TechniqueList"
import TraceTimeline from "../components/TraceTimeline"
import type { DemoExample } from "../lib/examples"

type Stage = "idle" | "ingesting" | "running" | "done" | "error"

async function resolveText(
  mode: InputMode,
  value: string | File,
): Promise<{ text: string; ingest: IngestResponse | null }> {
  if (mode === "text") return { text: value as string, ingest: null }
  if (mode === "html") {
    const ingest = await ingestHtml(value as string)
    return { text: ingest.text, ingest }
  }
  if (mode === "url") {
    const ingest = await ingestUrl(value as string)
    return { text: ingest.text, ingest }
  }
  const ingest = await ingestPdf(value as File)
  return { text: ingest.text, ingest }
}

export default function DemoPage() {
  const [stage, setStage] = useState<Stage>("idle")
  const [error, setError] = useState<string | null>(null)
  const [ingestPreview, setIngestPreview] = useState<IngestResponse | null>(null)
  const [advisory, setAdvisory] = useState<AdvisoryResponse | null>(null)

  const isRunning = stage === "ingesting" || stage === "running"

  async function run(mode: InputMode, value: string | File, reportId: string) {
    setStage("ingesting")
    setError(null)
    setAdvisory(null)
    setIngestPreview(null)
    try {
      const { text, ingest } = await resolveText(mode, value)
      setIngestPreview(ingest)
      setStage("running")
      const result = await getAdvisory(text, reportId)
      setAdvisory(result)
      setStage("done")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.")
      setStage("error")
    }
  }

  function handleExampleSelect(example: DemoExample) {
    void run("text", example.text, example.id)
  }

  function handleInputSubmit(mode: InputMode, value: string | File) {
    void run(mode, value, `demo-${Date.now()}`)
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <header className="mb-10">
        <h1 className="mb-2 text-3xl font-bold tracking-tight text-slate-50">Try it live</h1>
        <p className="text-slate-400">
          Runs the real backend — nothing here is mocked. Pick a canned example for a
          zero-typing tour of the two agentic decision branches, or bring your own
          report.
        </p>
      </header>

      <section className="mb-10">
        <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
          Canned examples
        </h2>
        <ExampleButtons onSelect={handleExampleSelect} disabled={isRunning} />
      </section>

      <section className="mb-10 rounded-xl border border-slate-800 bg-slate-900/30 p-6">
        <h2 className="mb-4 text-sm font-semibold tracking-wide text-slate-300 uppercase">
          Bring your own report
        </h2>
        <InputPanel onSubmit={handleInputSubmit} disabled={isRunning} />
      </section>

      {stage === "ingesting" && (
        <p className="mb-6 text-sm text-slate-500">Extracting plain text from the source…</p>
      )}
      {stage === "running" && (
        <p className="mb-6 text-sm text-slate-500">
          Running extraction → classification → triage…
        </p>
      )}

      {error && (
        <div className="mb-10 rounded-lg border border-red-500/40 bg-red-500/5 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {ingestPreview && (
        <section className="mb-10">
          <h2 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
            Extracted text
          </h2>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            {ingestPreview.title && (
              <div className="mb-2 font-medium text-slate-200">{ingestPreview.title}</div>
            )}
            <p className="line-clamp-4 text-sm whitespace-pre-line text-slate-500">
              {ingestPreview.text}
            </p>
          </div>
        </section>
      )}

      {advisory && (
        <section className="space-y-10">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-sm font-semibold tracking-wide text-slate-300 uppercase">Result</h2>
            <StatusBadge status={advisory.status} />
          </div>

          <div>
            <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
              Agent trace
            </h3>
            <TraceTimeline trace={advisory.trace} />
          </div>

          {advisory.extraction && (
            <div>
              <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
                Extraction
              </h3>
              <IOCTable extraction={advisory.extraction} />
            </div>
          )}

          {advisory.classification && (
            <div>
              <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
                Classification
              </h3>
              <TechniqueList classification={advisory.classification} />
            </div>
          )}

          {advisory.triage && (
            <div>
              <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
                Severity
              </h3>
              <div className="space-y-3">
                {advisory.triage.findings.map((finding, i) => (
                  <SeverityCard key={i} finding={finding} />
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="mb-3 text-sm font-semibold tracking-wide text-slate-300 uppercase">
              Rendered report
            </h3>
            <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm whitespace-pre-wrap text-slate-400">
              {advisory.report}
            </pre>
          </div>
        </section>
      )}
    </div>
  )
}
