# CTI/ICS Triage Tool

Agent-assisted cyber threat intelligence (CTI) triage for **OT/ICS** (operational
technology / industrial control systems) threat reports. It turns a raw threat report —
a CISA ICS-CERT advisory or a Dragos public OT report — into a structured,
severity-ranked security advisory, automating the tedious, high-volume parts of triage
while keeping the *judgment* (severity scoring especially) as interpretable rules rather
than a black-box model.

> **Status: extraction + classification working.** Triage and LangGraph orchestration
> are next (see [Roadmap](#roadmap)).

## What's implemented

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

Brings up the API plus Postgres/pgvector (the DB is unused in Day 1 but proves the infra):

```bash
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health
# {"status":"ok","app":"cti-triage"}
```

### Option B — Local (venv)

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

```bash
# macOS / Linux
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

Interactive API docs: <http://localhost:8000/docs>

## Using the endpoints

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

## Testing

```bash
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm   # needed for the NER / endpoint tests
pytest
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
app/
  main.py            FastAPI app (/health, /extract, /classify)
  config.py          settings (pydantic-settings)
  api/routes/        HTTP routes
  schemas/           Pydantic models (incl. the provenance model)
  extraction/        ioc.py · ner.py · provenance.py · service.py   <- implemented
  classification/    corpus.py · retrieval.py · reranking.py · service.py   <- implemented
  ingestion/         placeholder (later: PDF/HTML -> text)
  triage/            placeholder (next: severity cascade + clarification branch)
  orchestration/     placeholder (next: LangGraph agent graph + trace)
data/
  gazetteers/        curated threat-actor / ICS-vendor / sector lists
  classification/    committed ATT&CK-for-ICS technique corpus (79 techniques)
  samples/           sample report text (synthetic seed + your real reports)
research/            Phase-1 R&D: classification method bake-off + confidence calibration
tests/               pytest unit + endpoint tests
```

## Known limitations (Day 1)

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
- **The quality summary is a metric, not yet a decision.** The `proceed` /
  `flag_for_review` branch becomes real agent behaviour once orchestration exists.
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

## Roadmap

- ~~Extraction + classification as a plain pipeline; Phase-1 R&D bake-off to pick the
  ATT&CK-for-ICS mapping method.~~ **Done.**
- **Next** — Triage: a hand-designed, fully-traceable severity cascade (CVSS band ×
  exposure × asset-criticality × CISA KEV), with the *clarification-vs-guess* branch —
  the core agentic decision — as a real conditional edge. Then LangGraph orchestration
  wrapping extraction → classification → triage, with an agent trace log.
- **Later** — React frontend (advisory + agent trace side by side), scale evaluation to
  ~25 reports, and the writeup (precision/recall, ranking-agreement, limitations).
```
