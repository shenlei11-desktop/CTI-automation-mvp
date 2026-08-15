import { Link } from "react-router-dom"
import AgentGraphDiagram from "../components/AgentGraphDiagram"
import ClassificationFunnelDiagram from "../components/ClassificationFunnelDiagram"
import SeverityCascadeDiagram from "../components/SeverityCascadeDiagram"

const AGENTS = [
  {
    n: "01",
    name: "Ingestion",
    receives: "A report source: pasted text, raw HTML, a URL, or an uploaded PDF.",
    does: "Strips boilerplate (trafilatura for HTML, pypdf for PDF) — no per-site tuning needed.",
    emits: "Plain text, plus a proceed / flag_for_review quality signal.",
    decides: "Nothing judgment-related — mechanical text extraction only.",
  },
  {
    n: "02",
    name: "Extraction",
    receives: "Plain report text.",
    does: "Defang-aware regex for IOCs; curated gazetteers + spaCy NER for entities. Every fact keeps its source sentence.",
    emits: "IOCs, entities, and a signal-density quality score.",
    decides: "flag_for_review halts the run — a hard stop, not a soft warning. Classification and triage never see a report extraction doesn't trust.",
  },
  {
    n: "03",
    name: "Classification",
    receives: "Report text, auto-segmented into candidate behaviour sentences.",
    does: "Embedding retrieval narrows 79 techniques to 50, a cross-encoder reranks them — no LLM anywhere in this stage.",
    emits: "Ranked ATT&CK-for-ICS technique matches, deduped into a report-level rollup with supporting evidence.",
    decides: "flag_for_review per behaviour when the top two candidates are too close to call (margin-gated, not a probability threshold).",
  },
  {
    n: "04",
    name: "Triage",
    receives: "Report text (independently — does not wait on classification's output).",
    does: "Detects CVSS/exposure/asset-tier signals, checks the live CISA KEV catalog, runs a hand-designed severity cascade.",
    emits: "Per-CVE severity with a complete rule trace — every step, including no-ops.",
    decides: "needs_clarification when exposure or asset criticality can't be read from the text — a provisional score is still attached, never withheld.",
  },
  {
    n: "05",
    name: "Advisory",
    receives: "Everything the first four agents produced.",
    does: "Renders a plain-language advisory alongside the structured JSON.",
    emits: "The final response, plus the ordered trace of every node the run passed through.",
    decides: "Nothing new — this step is aggregation, not judgment.",
  },
]

const INPUTS = [
  { label: "Report text", detail: "via ingestion — pasted, fetched by URL, or uploaded as a PDF" },
  { label: "3 curated gazetteers", detail: "threat actors, ICS/OT vendors, targeted sectors" },
  { label: "79-technique ATT&CK-for-ICS corpus", detail: "with MITRE URLs and mitigation text" },
  { label: "Live CISA KEV catalog", detail: "cached snapshot, refreshed on a 24h TTL" },
  { label: "Exposure / asset-tier keyword lists", detail: "hand-curated, not learned" },
]

const TECH_STACK = [
  { name: "FastAPI + Pydantic", note: "Typed API contracts; every response is a validated schema." },
  { name: "spaCy", note: "Sentence-level provenance and generic NER." },
  { name: "fastembed", note: "bge-base-en-v1.5 + ms-marco-MiniLM-L-6-v2 — local, deterministic, no LLM." },
  { name: "LangGraph", note: "Real conditional edges, not a pipeline pretending to be one." },
  { name: "CISA KEV feed", note: "Exploitation status is checked, not assumed." },
  { name: "trafilatura + pypdf", note: "HTML/PDF → plain text." },
  { name: "React + TypeScript + Vite", note: "This app." },
  { name: "Docker Compose", note: "The whole stack, one command." },
]

export default function HomePage() {
  return (
    <div className="theme-document min-h-full">
      <div className="mx-auto max-w-3xl px-6 py-16">
        {/* Hero */}
        <header className="mb-16 border-b border-stone-300 pb-12">
          <p className="mb-3 font-mono text-xs tracking-widest text-red-800 uppercase">
            CTI / ICS Triage Tool
          </p>
          <h1 className="mb-5 font-serif text-4xl leading-tight font-semibold text-stone-900 sm:text-5xl">
            Automate the busywork.
            <br />
            Keep the judgment interpretable.
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-stone-600">
            Turns a raw OT/ICS threat report — a CISA advisory, a Dragos post, a PDF —
            into a structured, severity-ranked security advisory. Extraction and
            technique classification are automated. Severity scoring stays a fully
            traceable rule cascade, and the agent asks a human instead of guessing when
            it isn't confident.
          </p>
          <Link
            to="/demo"
            className="mt-7 inline-flex items-center gap-2 border border-red-800 px-5 py-2.5 font-mono text-sm font-medium text-red-800 transition-colors hover:bg-red-800 hover:text-stone-50"
          >
            Try it live →
          </Link>
        </header>

        {/* Purpose */}
        <section className="mb-16">
          <h2 className="mb-4 font-serif text-2xl font-semibold text-stone-900">
            Why it's built this way
          </h2>
          <div className="space-y-4 leading-relaxed text-stone-700">
            <p>
              CTI analysts spend most of their time on tedious, high-volume work:
              pulling IOCs and entities out of a report, mapping observed behaviour to
              MITRE ATT&CK-for-ICS techniques. That's exactly the kind of task
              automation is good at — fast, repetitive, pattern-matching.
            </p>
            <p>
              Severity triage is different. It's a judgment call with real
              consequences, and a black-box model that outputs "Critical" with no
              explanation isn't trustworthy enough to act on. So triage here is a
              hand-designed, fully-traceable rule cascade instead — every severity
              score comes with the exact chain of rules that produced it — and when the
              agent doesn't have enough information to score confidently, it says so
              and asks for clarification rather than silently guessing.
            </p>
            <p className="border-l-2 border-red-800 pl-4 font-serif text-lg text-stone-900 italic">
              Automate the mapping. Keep the judgment interpretable and auditable.
              That's the whole point.
            </p>
          </div>
        </section>

        {/* Agent graph */}
        <section className="mb-16">
          <h2 className="mb-2 font-serif text-2xl font-semibold text-stone-900">
            How a report flows through it
          </h2>
          <p className="mb-6 leading-relaxed text-stone-600">
            Five agents, wrapped in one LangGraph run. The dashed edge is a separate API
            call (ingestion, before the graph starts); the two solid branches off to the
            right are real conditional edges — the actual thesis, not just a flow chart.
          </p>
          <div className="border border-stone-300 bg-white p-6">
            <AgentGraphDiagram theme="light" />
          </div>
        </section>

        {/* Per-agent panels */}
        <section className="mb-16">
          <h2 className="mb-6 font-serif text-2xl font-semibold text-stone-900">
            What each agent does
          </h2>
          <div className="divide-y divide-stone-300 border-t border-b border-stone-300">
            {AGENTS.map((a) => (
              <div key={a.n} className="grid gap-x-6 gap-y-1.5 py-5 sm:grid-cols-[3rem_9rem_1fr]">
                <div className="font-mono text-sm text-stone-400">{a.n}</div>
                <div className="font-serif text-lg font-semibold text-stone-900">{a.name}</div>
                <dl className="space-y-1 text-sm text-stone-600">
                  <div>
                    <dt className="inline font-medium text-stone-800">Receives — </dt>
                    <dd className="inline">{a.receives}</dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-stone-800">Does — </dt>
                    <dd className="inline">{a.does}</dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-stone-800">Emits — </dt>
                    <dd className="inline">{a.emits}</dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-red-800">Decides — </dt>
                    <dd className="inline">{a.decides}</dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>
        </section>

        {/* Classification funnel */}
        <section className="mb-16">
          <h2 className="mb-2 font-serif text-2xl font-semibold text-stone-900">
            How classification actually works
          </h2>
          <p className="mb-6 leading-relaxed text-stone-600">
            No LLM anywhere in this stage — architecturally incapable of hallucinating a
            technique ID, since the reranker only ever reorders candidates it was
            given.
          </p>
          <div className="border border-stone-300 bg-white p-6">
            <ClassificationFunnelDiagram theme="light" />
          </div>
        </section>

        {/* Severity cascade */}
        <section className="mb-16">
          <h2 className="mb-2 font-serif text-2xl font-semibold text-stone-900">
            How severity is scored
          </h2>
          <p className="mb-6 leading-relaxed text-stone-600">
            A hand-designed ladder, not a black box — every step is a named rule with a
            plain-language reason.
          </p>
          <div className="border border-stone-300 bg-white p-6">
            <SeverityCascadeDiagram theme="light" />
          </div>
        </section>

        {/* Inputs */}
        <section className="mb-16">
          <h2 className="mb-6 font-serif text-2xl font-semibold text-stone-900">
            What feeds the system
          </h2>
          <ul className="divide-y divide-stone-300 border-t border-b border-stone-300">
            {INPUTS.map((i) => (
              <li key={i.label} className="flex flex-wrap justify-between gap-x-4 gap-y-1 py-3">
                <span className="font-medium text-stone-800">{i.label}</span>
                <span className="text-sm text-stone-500">{i.detail}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Tech stack */}
        <section className="mb-16">
          <h2 className="mb-6 font-serif text-2xl font-semibold text-stone-900">Tech stack</h2>
          <ul className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {TECH_STACK.map((item) => (
              <li key={item.name} className="border-l-2 border-stone-300 py-0.5 pl-4">
                <div className="font-medium text-stone-800">{item.name}</div>
                <div className="text-sm text-stone-500">{item.note}</div>
              </li>
            ))}
          </ul>
        </section>

        {/* CTA */}
        <section className="border border-stone-300 bg-white p-8 text-center">
          <h2 className="mb-2 font-serif text-2xl font-semibold text-stone-900">See it run</h2>
          <p className="mx-auto mb-6 max-w-md text-stone-600">
            Paste a report, fetch a real advisory by URL, or upload a PDF — or click one
            of three canned examples that walk through the pipeline's two agentic
            decision branches.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 border border-red-800 px-5 py-2.5 font-mono text-sm font-medium text-red-800 transition-colors hover:bg-red-800 hover:text-stone-50"
          >
            Try it live →
          </Link>
        </section>
      </div>
    </div>
  )
}
