# CTI/ICS Triage Tool

Agent-assisted cyber threat intelligence (CTI) triage for **OT/ICS** (operational
technology / industrial control systems) threat reports. It turns a raw threat report —
a CISA ICS-CERT advisory or a Dragos public OT report — into a structured,
severity-ranked security advisory, automating the tedious, high-volume parts of triage
while keeping the *judgment* (severity scoring especially) as interpretable rules rather
than a black-box model.

> **Status: the full pipeline and web app are working end to end.** Ingestion,
> extraction, classification, triage, LangGraph orchestration (wrapping the middle
> three into one agent graph, with real conditional edges and a trace log), and a
> two-page React frontend are all implemented — see [Roadmap](#roadmap) for what's next.

## The web app

A two-page React + TypeScript + Tailwind app in [`frontend/`](frontend/), talking
directly to the FastAPI backend (no separate backend-for-frontend layer):

- **Overview** (`/`) — the pitch: what the tool is and why it's built this way, a
  walkthrough of the five-stage pipeline, the tech stack, and a hand-built diagram
  that calls out the two agentic decision branches, not just a generic flow chart.
- **Try It** (`/demo`) — the proof: paste text/HTML, fetch a real report by URL, or
  upload a PDF and run it through the real backend, live. Three canned examples give
  a zero-typing tour of both decision branches (`needs_extraction_review`,
  `needs_clarification`) plus the fully-scored happy path, each hand-verified against
  the running backend. Results render the full agent trace, extracted IOCs/entities,
  ATT&CK-for-ICS matches, and per-CVE severity with its complete rule trace.

## What's implemented

`POST /ingest` (text/HTML/URL) and `POST /ingest/pdf` (file upload) turn a report
source into the plain text the rest of the pipeline expects:

- **HTML** (raw markup or fetched by URL) goes through `trafilatura`'s main-content
  extraction — strips nav/ads/boilerplate without needing per-site tuning, since a real
  CISA advisory page and a Dragos blog post don't share a layout.
- **PDF** (file upload or fetched by URL) goes through `pypdf`.
- **URL fetch** sniffs `Content-Type` and dispatches to whichever extractor applies;
  verified this session against a real, uncurated, just-published CISA advisory (not a
  fixture) — boilerplate stripped cleanly, and the resulting text fed straight into
  `/advisory` end-to-end with no manual cleanup.
- Same quality-gate pattern as extraction: too little text after extraction →
  `flag_for_review` rather than silently handing the rest of the pipeline junk.

`POST /extract` takes raw report text and returns:

- **IOCs** — IPv4 addresses, domains, MD5/SHA1/SHA256 hashes, and CVEs, extracted with
  **defang-aware** regex (`192[.]168[.]1[.]1`, `hxxps://evil[.]com` are handled), each
  with both the as-found (`value_raw`) and canonical (`value_normalized`) form.
- **Entities** — threat actors, ICS/OT vendors, and targeted sectors via curated
  **gazetteers**, plus generic organizations/locations/people via spaCy NER.
- **Provenance** — every extracted fact carries the **source sentence** and character
  offsets it came from.
- **Quality summary** — a lightweight signal (`proceed` / `flag_for_review`) that the
  extraction agent will later branch on in orchestration.

`POST /classify` takes attacker-behaviour text and returns ranked **MITRE ATT&CK-for-ICS**
technique matches:

- **Method D** (chosen after a [Phase-1 R&D bake-off](research/README.md) comparing
  embeddings, LLM-only, hybrid, and retrieve+rerank): embedding retrieval
  (`bge-base-en-v1.5`) narrows the 79-technique catalogue to a shortlist, then a
  cross-encoder (`ms-marco-MiniLM-L-6-v2`) reranks it — fully local, deterministic, no
  LLM in the loop, and architecturally incapable of hallucinating a technique ID.
- **Confidence gate**: the top1-vs-top2 score margin is checked against a threshold
  *derived empirically* from 259 real labeled examples (Youden's-J analysis — see
  [`research/classification_confidence_calibration.ipynb`](research/classification_confidence_calibration.ipynb)),
  not guessed. Below the margin → `flag_for_review` rather than a confident-looking
  wrong answer.

`POST /triage` takes raw report text and returns a **fully-traceable severity
assessment** per CVE:

- **The severity cascade**: base band from the official FIRST.org CVSS v3.x scale,
  then exposure (internet-facing / segmented) and asset-criticality tier
  (safety-critical / process-critical / monitoring-only) each step the band up/down one
  ordinal notch, then CISA **KEV** listing floors the result at High regardless of the
  other factors. Every step — including no-ops — is recorded in a `rule_trace`, so
  every severity score shows exactly which rule produced it.
- **The core agentic decision**: if exposure or asset-criticality tier can't be
  confidently determined from the report text, triage flags `needs_clarification`
  (with a provisional score still attached, never withheld) instead of guessing.
  Deliberately does *not* trigger on missing CVSS, which gets a documented neutral
  default (Medium) instead.
- **KEV is checked independently**, not trusted from the report text — the bundled
  sample advisory *claims* KEV listing, but the real CISA feed shows this fictional CVE
  as `not_listed`, and the system reports that honestly rather than taking the report's
  word for it.

`POST /advisory` wraps all three into one **LangGraph** agent and returns a single
structured advisory plus a step-by-step trace:

- **Two real conditional edges** — the point of the whole module. If extraction flags
  `flag_for_review`, the graph **hard-stops**: classification and triage never run, and
  the response's `classification`/`triage` fields come back `null` rather than pretending
  a distrusted input produced a trustworthy result. If triage's decision comes back
  `needs_clarification`, the graph still attaches the provisional finding — the agent's
  "ask a human instead of guessing" moment is visible in the trace, not silent.
- **`status`** on the response is one of `completed`, `needs_extraction_review`, or
  `needs_clarification`, so a caller always knows *why* a run didn't reach a clean finish.
- **`trace`** is an ordered list of `{node, detail}` entries — every node the run passed
  through and a plain-language summary of what it did, so the whole decision path is
  auditable after the fact, not just the final answer.
- **`report`** is a human-readable rendered advisory (technique matches, per-CVE
  severity with its full rule trace, and any review/clarification caveat spelled out)
  alongside the structured JSON.

## Design decisions worth noting

- **Defang handling is in place from day one.** Real reports defang indicators; a naive
  regex misses most of them. Patterns match defanged forms *in place* in the original
  text so character offsets (and therefore provenance) stay valid — we normalize only the
  matched substring, never the whole document.
- **Gazetteers over a black-box classifier** for domain entities. A curated list of
  threat actors / ICS vendors / sectors is interpretable, auditable, and itself a
  domain-knowledge artifact — a better fit for the project's thesis than an opaque model.
- **Provenance is a schema-level guarantee,** not an afterthought — see
  [`app/schemas/extraction.py`](app/schemas/extraction.py).

## Quickstart

### Option A — Docker Compose (full stack)

Brings up the API, the web app, and Postgres/pgvector (the DB is currently unused but
proves the infra; see [Known limitations](#known-limitations)):

```bash
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health
# {"status":"ok","app":"cti-triage"}
```

Web app: <http://localhost:4173>

### Option B — Local (venv + npm)

One-time setup:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
cd frontend; npm install; cd ..
```

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
(cd frontend && npm install)
```

Then, every time you want to run it — one command starts both the backend
(`uvicorn --reload`) and the frontend (`vite`) together:

```powershell
# Windows PowerShell
.\dev.ps1
```

```bash
# macOS / Linux
./dev.sh
```

Interactive API docs: <http://localhost:8000/docs> · Web app: <http://localhost:5173>

## Using the endpoints

```bash
# curl — /ingest, fetch a real CISA advisory by URL
curl -X POST http://localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"url","url":"https://www.cisa.gov/news-events/ics-advisories/icsa-26-204-01"}'
```

```bash
# curl — /ingest/pdf, upload a PDF report
curl -X POST http://localhost:8000/ingest/pdf -F "file=@path/to/advisory.pdf"
```

Abridged response (either route):

```json
{
  "text": "Johnson Controls C-CURE 9000 and Victor application server (Update A)\nSummary\n...",
  "title": "Johnson Controls C-CURE 9000 and Victor application server (Update A) | CISA",
  "source_type": "url",
  "quality": { "recommendation": "proceed", "reason": "Extracted 11865 chars of usable text." }
}
```

Feed the returned `text` straight into `/extract`, `/classify`, `/triage`, or
`/advisory` — ingestion's job ends at clean plain text, it doesn't call the rest of the
pipeline itself.

```powershell
# PowerShell — run the bundled synthetic advisory through /extract
$body = @{
  text      = (Get-Content -Raw data/samples/sample_advisory_01.txt)
  report_id = "sample-01"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/extract `
  -ContentType application/json -Body $body | ConvertTo-Json -Depth 6
```

```bash
# curl
curl -X POST http://localhost:8000/extract \
  -H 'Content-Type: application/json' \
  -d '{"text":"Beaconing to 185[.]220[.]101[.]45 and hxxps://update-modicon[.]net; CVE-2026-2841. Attributed to VOLTZITE targeting Schneider Electric Modicon.","report_id":"demo"}'
```

Abridged response shape:

```json
{
  "report_id": "demo",
  "iocs": [
    {
      "type": "ipv4",
      "value_raw": "185[.]220[.]101[.]45",
      "value_normalized": "185.220.101.45",
      "is_private": false,
      "source": { "sentence": "Beaconing to 185[.]220[.]101[.]45 ...", "start": 13, "end": 33 }
    },
    { "type": "domain", "value_raw": "update-modicon[.]net", "value_normalized": "update-modicon.net", "is_private": null, "source": { "...": "..." } },
    { "type": "cve", "value_raw": "CVE-2026-2841", "value_normalized": "CVE-2026-2841", "is_private": null, "source": { "...": "..." } }
  ],
  "entities": [
    { "type": "threat_actor", "text": "VOLTZITE", "method": "gazetteer", "source": { "...": "..." } },
    { "type": "ics_vendor", "text": "Schneider Electric", "method": "gazetteer", "source": { "...": "..." } }
  ],
  "quality": {
    "n_iocs": 3, "n_entities": 2, "text_length": 138,
    "signal_density": 36.23, "recommendation": "flag_for_review",
    "reason": "Report text is very short (138 chars); likely a parsing failure or a stub..."
  }
}
```

```bash
# curl — /classify
curl -X POST http://localhost:8000/classify \
  -H 'Content-Type: application/json' \
  -d '{"behaviors":[{"text":"The threat actor identified a PLC whose web-based management interface was directly reachable from the public internet and exploited an authentication bypass to gain access without valid credentials."}],"top_k":3}'
```

Abridged response:

```json
{
  "behaviors": [
    {
      "text": "The threat actor identified a PLC...",
      "matches": [
        { "technique_id": "T0883", "technique_name": "Internet Accessible Device",
          "tactics": ["initial-access"], "retrieval_score": 0.634, "rerank_score": -1.768 },
        { "technique_id": "T0819", "technique_name": "Exploit Public-Facing Application",
          "tactics": ["initial-access"], "retrieval_score": 0.597, "rerank_score": -3.784 }
      ],
      "quality": {
        "top1_score": -1.77, "top1_margin": 2.02,
        "recommendation": "proceed",
        "reason": "Top match scored -1.77, 2.02 clear of the runner-up."
      }
    }
  ]
}
```

`rerank_score` is a raw, unbounded cross-encoder logit — not a probability. `top1_margin`
(the gap to the runner-up) is what the confidence gate actually thresholds on.

```powershell
# PowerShell — /triage, run the bundled sample advisory
$body = @{
  text      = (Get-Content -Raw data/samples/sample_advisory_01.txt)
  report_id = "sample-01"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/triage `
  -ContentType application/json -Body $body | ConvertTo-Json -Depth 6
```

```bash
# curl
curl -X POST http://localhost:8000/triage \
  -H 'Content-Type: application/json' \
  -d '{"text":"A vulnerability tracked as CVE-2026-9999 has a CVSS v3.1 base score of 8.1. The interface is internet-facing and controls a safety-critical process.","report_id":"demo"}'
```

Abridged response:

```json
{
  "context": { "exposure": "internet_facing", "asset_tier": "safety_critical" },
  "findings": [
    {
      "cve_id": "CVE-2026-2841", "cvss_score": 9.8, "kev_status": "not_listed",
      "severity": "Critical",
      "rule_trace": [
        { "rule": "cvss_base", "detail": "CVSS score 9.8 maps to base band Critical.", "resulting_band": "Critical" },
        { "rule": "exposure", "detail": "Internet-facing: escalated one band.", "resulting_band": "Critical" },
        { "rule": "asset_tier", "detail": "Safety-critical asset: escalated one band.", "resulting_band": "Critical" },
        { "rule": "kev", "detail": "not confirmed exploited; no adjustment applied.", "resulting_band": "Critical" }
      ]
    }
  ],
  "quality": { "decision": "scored", "reason": "Exposure and asset-criticality tier were both specified..." }
}
```

```powershell
# PowerShell — /advisory, the full agent pipeline in one call
$body = @{
  text      = (Get-Content -Raw data/samples/sample_advisory_01.txt)
  report_id = "sample-01"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/advisory `
  -ContentType application/json -Body $body | ConvertTo-Json -Depth 8
```

```bash
# curl
curl -X POST http://localhost:8000/advisory \
  -H 'Content-Type: application/json' \
  -d '{"text":"...","report_id":"demo"}'
```

Abridged response:

```json
{
  "report_id": "sample-01",
  "status": "completed",
  "trace": [
    { "node": "extraction", "detail": "Extracted 6 IOC(s) and 3 entity(ies); recommendation: proceed." },
    { "node": "classification", "detail": "Classified 11 behaviour(s) into ATT&CK-for-ICS techniques." },
    { "node": "triage", "detail": "Scored 1 finding(s); decision: scored." },
    { "node": "finalize", "detail": "Pipeline completed; advisory ready." }
  ],
  "extraction": { "...": "same shape as /extract" },
  "classification": { "...": "same shape as /classify" },
  "triage": { "...": "same shape as /triage" },
  "report": "Advisory for report: sample-01\n\nATT&CK-for-ICS techniques observed:\n  - T0883 Internet Accessible Device ...\n\nSeverity (exposure: internet_facing, asset tier: safety_critical):\n  - CVE-2026-2841: Critical (KEV: not_listed)\n      * cvss_base: CVSS score 9.8 maps to base band Critical.\n      ...\n\nStatus: completed"
}
```

A short stub text (e.g. `"too short"`) demonstrates the hard stop instead:
`status` comes back `needs_extraction_review`, `trace` is just
`["extraction", "needs_extraction_review"]`, and `classification`/`triage` are both
`null` — proving classification and triage genuinely never ran, rather than having run
and been discarded.

## Testing

```bash
# backend
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm   # needed for the NER / endpoint tests
pytest
```

```bash
# frontend -- lint + type-check + build (no component/e2e test suite, see
# Known limitations)
cd frontend
npm ci
npm run lint
npm run build
```

## Branching & CI

Trunk-based: `main` is always stable and protected. Work happens on short-lived branches
merged via PR, named by type:

- `feat/<name>` — new functionality (e.g. `feat/classification-bakeoff`)
- `fix/<name>` — bug fixes
- `chore/<name>` — tooling, CI, docs, dependencies

Every push and PR runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml): lint
(`ruff`), tests (`pytest`), and a Docker image build. `main` requires these checks to
pass before merging.

## Repository layout

```
dev.ps1 / dev.sh    one-command local dev launcher: backend + frontend together
app/
  main.py            FastAPI app (/health, /ingest, /extract, /classify, /triage, /advisory)
  config.py          settings (pydantic-settings)
  api/routes/        HTTP routes
  schemas/           Pydantic models (incl. the provenance model)
  ingestion/         html_extract.py · pdf_extract.py · url_fetch.py · service.py  <- implemented
  extraction/        ioc.py · ner.py · provenance.py · service.py   <- implemented
  classification/    corpus.py · retrieval.py · reranking.py · service.py   <- implemented
  triage/            signals.py · kev.py · cascade.py · service.py  <- implemented
  orchestration/     state.py · nodes.py · graph.py · report.py     <- implemented
data/
  gazetteers/        curated threat-actor / ICS-vendor / sector lists
  classification/    committed ATT&CK-for-ICS technique corpus (79 techniques)
  triage/            curated exposure / asset-criticality-tier keyword lists
  kev/               committed CISA Known Exploited Vulnerabilities snapshot
  samples/           sample report text (synthetic seed + your real reports)
research/            Phase-1 R&D: classification method bake-off + confidence calibration
tests/               pytest unit + endpoint tests
frontend/            React + TypeScript + Tailwind web app <- implemented
  src/api/           typed fetch client + TS types mirroring the Pydantic schemas
  src/pages/         HomePage.tsx (overview) · DemoPage.tsx (interactive demo)
  src/components/    ArchitectureDiagram, StatusBadge, TraceTimeline, IOCTable,
                      TechniqueList, SeverityCard, InputPanel, ExampleButtons
```

## Known limitations

Documented honestly rather than hidden — an expanded version will ship with the final writeup.

- **Domain vs. filename ambiguity.** A blocklist of common file extensions
  (`report.pdf`, `payload.exe`) suppresses filename false positives, but a few real TLDs
  (`.zip`, `.sh`) are also file extensions and may be dropped.
- **`1.2.3.4`-style ambiguity.** A dotted quad with all octets ≤ 255 is treated as an
  IPv4 address even when it is really a version string.
- **Gazetteer recall is bounded by the lists.** Unlisted or novel threat actors / vendors
  are only caught by generic spaCy NER (as `organization`), if at all.
- **Sentence segmentation is rule-based** (spaCy `sentencizer`), so provenance can be off
  on unusual formatting (tables, bullet fragments).
- **Classification's confidence threshold isn't rigorously cross-validated.** It's
  *derived*, not guessed — a Youden's-J search over 259 real labeled examples — but
  that's still not enough data over 79 classes with a general-purpose reranker to trust
  as a calibrated boundary. Read it as "catches many wrong answers, avoids flagging most
  right ones," not a probability cutoff. See the calibration notebook for the honest
  numbers.
- **No ICS-domain embedding/reranker model exists** via the local `fastembed` library —
  `bge`/`ms-marco` are general-purpose web-search models. This is a real ceiling on
  classification accuracy, not a bug.
- **Automatic whole-report chunking for classification (`classify_text`, used by the
  orchestration agent) is an unvalidated heuristic** — sentence-splitting was never
  exercised by the bake-off, which worked on pre-curated behaviour snippets. The
  standalone `/classify` endpoint avoids this by requiring the caller to supply
  behaviours explicitly.
- **Exposure/asset-tier detection is plain keyword matching**, not NLP — it can't
  distinguish a current-state claim from a recommendation (e.g. "the interface is
  internet-facing... operators should segment the network" resolves to `unknown`,
  correctly but conservatively) or catch novel phrasing outside the curated lists.
- **CVE-to-CVSS pairing is same-sentence-or-nothing.** A report with several CVEs and
  several CVSS mentions spread across paragraphs will leave some CVEs unassociated
  rather than guess a wrong pairing.
- **The severity cascade's specific rule design (band-stepping, KEV-as-floor, the
  neutral CVSS default) is a considered but original design**, not derived from a
  published standard beyond the CVSS band boundaries themselves — a legitimate
  alternative (e.g. numeric multipliers) exists and was deliberately not chosen; see
  `app/triage/cascade.py`'s docstring for the reasoning.
- **Postgres/pgvector runs in `docker-compose.yml` but nothing uses it.** The
  classification corpus is only 79 vectors — trivial in-memory numpy, no DB needed for
  correctness at this scale. A better eventual use is persisting orchestration's agent
  trace / advisory audit trail, not vector search.
- **The graph is strictly sequential and stateless between calls.** No parallel
  fan-out (classification and triage both only need `text`, but run one after the
  other, not concurrently), and no checkpointing — each `/advisory` call runs start to
  finish in one request with nothing persisted, so a run can't be paused, replayed, or
  resumed. Fine at this scale; would need addressing before this became a long-running
  or multi-report batch service.
- **`classify_text`'s unvalidated chunking heuristic (above) is exactly what powers
  `/advisory`'s classification step.** The standalone `/classify` endpoint sidesteps
  this by taking caller-supplied behaviours directly, but the orchestrated pipeline has
  no such escape hatch — it always auto-chunks.
- **PDF extraction is text-order, not layout-aware.** Table-heavy sections (e.g. an
  affected-versions table) may not extract in a sensible reading order. Pasting text
  directly remains available as a fallback when this matters.
- **URL fetch has no SSRF allowlist.** `/ingest` will fetch whatever URL it's given,
  server-side. Acceptable for a local, single-user portfolio tool; would need an
  allowlist/egress policy before this ran as a shared or public service.
- **Ingestion isn't wired into the LangGraph graph as its own node.** `/advisory` still
  takes plain text; turning a URL/PDF into an advisory in one call means calling
  `/ingest` first and passing its `text` to `/advisory` — a deliberate choice to keep
  the already-tested graph untouched, not an oversight.
- **The web app is local-only by design.** No public deployment, no prod CORS origin
  configured — `cors_origins` in `app/config.py` only allows the local Vite dev/preview
  ports. Deploying it publicly would need picking hosts, wiring a prod origin, and an
  API base URL that isn't a hardcoded `localhost:8000` fallback.
- **No automated frontend tests.** CI runs `oxlint` + a TypeScript build (`tsc -b`) on
  every push, which catches type errors and lint issues, but there's no component or
  end-to-end test suite — reasonable for a two-page portfolio app, verified this
  session by hand (dev server, production preview build, and the full
  `docker compose up --build` stack, all against the real backend) rather than by
  Playwright/RTL.
- **The TS types in `frontend/src/api/types.ts` are hand-kept in sync with the Pydantic
  schemas**, not generated. A backend field rename won't fail loudly on the frontend
  side until something actually breaks at runtime.

## Roadmap

- ~~Extraction + classification as a plain pipeline; Phase-1 R&D bake-off to pick the
  ATT&CK-for-ICS mapping method.~~ **Done.**
- ~~Triage: a hand-designed, fully-traceable severity cascade (CVSS band × exposure ×
  asset-criticality × CISA KEV), with the *clarification-vs-guess* branch — the core
  agentic decision.~~ **Done.**
- ~~LangGraph orchestration wrapping extraction → classification → triage, with the
  extraction and triage decisions as real conditional edges, plus an agent trace
  log.~~ **Done.**
- ~~Ingestion: PDF/HTML/URL → plain text.~~ **Done.**
- ~~A two-page React web app: an overview page (purpose, workflow, tech stack,
  architecture diagram) and an interactive demo page against the real backend.~~ **Done.**
- **Next** — scale evaluation to ~25 reports, and the writeup (precision/recall,
  ranking-agreement, limitations).
