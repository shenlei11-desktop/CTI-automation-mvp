import { Link } from "react-router-dom"
import ArchitectureDiagram from "../components/ArchitectureDiagram"

const TECH_STACK = [
  { name: "FastAPI + Pydantic", note: "Typed API contracts; every response is a validated schema, not loose JSON." },
  { name: "spaCy", note: "Sentence-level provenance and generic NER, no downloaded model needed for segmentation." },
  { name: "fastembed", note: "bge-base-en-v1.5 embeddings + ms-marco-MiniLM-L-6-v2 cross-encoder — local, deterministic, no LLM." },
  { name: "LangGraph", note: "The orchestration agent: real conditional edges, not a fixed pipeline pretending to be one." },
  { name: "CISA KEV feed", note: "Live-refreshed, cached snapshot fallback — exploitation status is checked, not assumed." },
  { name: "trafilatura + pypdf", note: "HTML/PDF → plain text, boilerplate stripped without per-site tuning." },
  { name: "React + TypeScript + Vite", note: "This app." },
  { name: "Docker Compose", note: "The whole stack, one command." },
]

export default function HomePage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      {/* Hero */}
      <section className="mb-20 text-center">
        <p className="mb-3 text-sm font-medium tracking-wide text-teal-400 uppercase">
          CTI / ICS Triage Tool
        </p>
        <h1 className="mb-5 text-4xl font-bold tracking-tight text-slate-50 sm:text-5xl">
          Automate the busywork.
          <br />
          Keep the judgment interpretable.
        </h1>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-slate-400">
          Turns a raw OT/ICS threat report — a CISA advisory, a Dragos post, a PDF —
          into a structured, severity-ranked security advisory. Extraction and
          technique classification are automated. Severity scoring stays a fully
          traceable rule cascade, and the agent asks a human instead of guessing when
          it isn't confident.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-500 px-5 py-2.5 font-semibold text-slate-950 transition-colors hover:bg-teal-400"
        >
          Try it live →
        </Link>
      </section>

      {/* Purpose */}
      <section className="mb-20">
        <h2 className="mb-4 text-xl font-semibold text-slate-100">Why it's built this way</h2>
        <div className="space-y-4 text-slate-400">
          <p>
            CTI analysts spend most of their time on tedious, high-volume work: pulling
            IOCs and entities out of a report, mapping observed behaviour to MITRE
            ATT&CK-for-ICS techniques. That's exactly the kind of task AI is good at —
            fast, repetitive, pattern-matching.
          </p>
          <p>
            Severity triage is different. It's a judgment call with real consequences,
            and a black-box model that outputs "Critical" with no explanation isn't
            trustworthy enough to act on. So triage here is a hand-designed,
            fully-traceable rule cascade instead — every severity score comes with the
            exact chain of rules that produced it — and when the agent doesn't have
            enough information to score confidently, it says so and asks for
            clarification rather than silently guessing.
          </p>
          <p>
            That split — automate the mapping, keep the judgment interpretable and
            auditable — is the whole point of the project.
          </p>
        </div>
      </section>

      {/* Architecture */}
      <section className="mb-20">
        <h2 className="mb-2 text-xl font-semibold text-slate-100">How a report flows through it</h2>
        <p className="mb-8 text-slate-400">
          Five stages, wrapped in one LangGraph agent. The two highlighted branches are
          the actual thesis in action — not just a pipeline diagram.
        </p>
        <ArchitectureDiagram />
      </section>

      {/* Tech stack */}
      <section className="mb-20">
        <h2 className="mb-6 text-xl font-semibold text-slate-100">Tech stack</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {TECH_STACK.map((item) => (
            <div key={item.name} className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
              <div className="mb-1 font-medium text-slate-200">{item.name}</div>
              <div className="text-sm text-slate-500">{item.note}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center">
        <h2 className="mb-2 text-xl font-semibold text-slate-100">See it run</h2>
        <p className="mb-6 text-slate-400">
          Paste a report, fetch a real advisory by URL, or upload a PDF — or just click
          one of three canned examples that walk through the pipeline's two
          agentic decision branches.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-500 px-5 py-2.5 font-semibold text-slate-950 transition-colors hover:bg-teal-400"
        >
          Try it live →
        </Link>
      </section>
    </div>
  )
}
