import { useState } from "react"
import { ApiError, getAdvisory, ingestHtml, ingestPdf, ingestUrl } from "../api/client"
import type { AdvisoryResponse, FeedItem, IngestResponse } from "../api/types"
import AgentGraphDiagram from "../components/AgentGraphDiagram"
import ExampleButtons from "../components/ExampleButtons"
import InputPanel, { type InputMode } from "../components/InputPanel"
import IOCTable from "../components/IOCTable"
import LiveAdvisoryPicker from "../components/LiveAdvisoryPicker"
import SeverityCard from "../components/SeverityCard"
import StatusBadge from "../components/StatusBadge"
import TechniqueList from "../components/TechniqueList"
import TraceTimeline from "../components/TraceTimeline"
import TriageContextPanel from "../components/TriageContextPanel"
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
  const [didIngest, setDidIngest] = useState(false)

  const isRunning = stage === "ingesting" || stage === "running"

  async function run(mode: InputMode, value: string | File, reportId: string) {
    setStage("ingesting")
    setError(null)
    setAdvisory(null)
    setIngestPreview(null)
    setDidIngest(mode !== "text")
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

  function handleFeedSelect(item: FeedItem) {
    void run("url", item.url, item.url)
  }

  function handleInputSubmit(mode: InputMode, value: string | File) {
    void run(mode, value, `demo-${Date.now()}`)
  }

  const activeTrace = advisory
    ? [...(didIngest ? ["ingestion"] : []), ...advisory.trace.map((t) => t.node)]
    : isRunning
      ? didIngest
        ? ["ingestion"]
        : []
      : undefined

  return (
    <div className="theme-console min-h-full">
      <div className="mx-auto max-w-4xl px-6 py-16">
        <header className="mb-10">
          <h1 className="mb-2 font-serif text-3xl font-semibold text-stone-100">Try it live</h1>
          <p className="text-stone-500">
            Runs the real backend — nothing here is mocked. Pick a live advisory or a
            canned example for a zero-typing tour, or bring your own report.
          </p>
        </header>

        <section className="mb-10">
          <h2 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
            Live from CISA, right now
          </h2>
          <LiveAdvisoryPicker onSelect={handleFeedSelect} disabled={isRunning} />
        </section>

        <section className="mb-10">
          <h2 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
            Canned scenarios (guaranteed to hit each branch)
          </h2>
          <ExampleButtons onSelect={handleExampleSelect} disabled={isRunning} />
        </section>

        <section className="mb-10 border border-stone-800 bg-stone-900/20 p-6">
          <h2 className="mb-4 font-mono text-xs tracking-wide text-stone-500 uppercase">
            Bring your own report
          </h2>
          <InputPanel onSubmit={handleInputSubmit} disabled={isRunning} />
        </section>

        {error && (
          <div className="mb-10 border border-red-500/40 bg-red-500/5 p-4 font-mono text-sm text-red-300">
            {error}
          </div>
        )}

        {ingestPreview && (
          <section className="mb-10">
            <h2 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
              Extracted text
            </h2>
            <div className="border border-stone-800 bg-stone-900/40 p-4">
              {ingestPreview.title && (
                <div className="mb-2 font-medium text-stone-200">{ingestPreview.title}</div>
              )}
              <p className="line-clamp-4 text-sm whitespace-pre-line text-stone-500">
                {ingestPreview.text}
              </p>
            </div>
          </section>
        )}

        {(isRunning || advisory) && (
          <section className="mb-10">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-mono text-xs tracking-wide text-stone-500 uppercase">
                Agent run
              </h2>
              {advisory && <StatusBadge status={advisory.status} />}
              {isRunning && <span className="font-mono text-xs text-amber-500">running…</span>}
            </div>
            <div className="border border-stone-800 bg-stone-950 p-6">
              <AgentGraphDiagram theme="dark" activeTrace={activeTrace} />
            </div>
            {advisory && (
              <div className="mt-4">
                <TraceTimeline trace={advisory.trace} />
              </div>
            )}
          </section>
        )}

        {advisory && (
          <section className="space-y-10">
            {advisory.extraction && (
              <div>
                <h3 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
                  Extraction
                </h3>
                <IOCTable extraction={advisory.extraction} />
              </div>
            )}

            {advisory.classification && (
              <div>
                <h3 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
                  Classification — techniques observed
                </h3>
                <TechniqueList techniques={advisory.classification.techniques} />
              </div>
            )}

            {advisory.triage && (
              <div>
                <h3 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
                  Severity
                </h3>
                <TriageContextPanel triage={advisory.triage} />
                <div className="space-y-4">
                  {advisory.triage.findings.map((finding, i) => (
                    <SeverityCard key={i} finding={finding} />
                  ))}
                </div>
              </div>
            )}

            <div>
              <h3 className="mb-3 font-mono text-xs tracking-wide text-stone-500 uppercase">
                Rendered report
              </h3>
              <pre className="overflow-x-auto border border-stone-800 bg-stone-900/40 p-4 text-sm whitespace-pre-wrap text-stone-400">
                {advisory.report}
              </pre>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
