# CTI/ICS Triage Tool

Agent-assisted cyber threat intelligence (CTI) triage for **OT/ICS** (operational
technology / industrial control systems) threat reports. It turns a raw threat report —
a CISA ICS-CERT advisory or a Dragos public OT report — into a structured,
severity-ranked security advisory, automating the tedious, high-volume parts of triage
while keeping the *judgment* (severity scoring especially) as interpretable rules rather
than a black-box model.

> **Status: Day 1 — extraction only.** This slice stands up the repo, local infra, and a
> single working `POST /extract` endpoint. Classification, triage, and LangGraph
> orchestration are intentionally not built yet (see [Roadmap](#roadmap)).

## What Day 1 does

`POST /extract` takes raw report text and returns:

- **IOCs** — IPv4 addresses, domains, MD5/SHA1/SHA256 hashes, and CVEs, extracted with
  **defang-aware** regex (`192[.]168[.]1[.]1`, `hxxps://evil[.]com` are handled), each
  with both the as-found (`value_raw`) and canonical (`value_normalized`) form.
- **Entities** — threat actors, ICS/OT vendors, and targeted sectors via curated
  **gazetteers**, plus generic organizations/locations/people via spaCy NER.
- **Provenance** — every extracted fact carries the **source sentence** and character
  offsets it came from.
- **Quality summary** — a lightweight signal (`proceed` / `flag_for_review`) that the
  Week-2 extraction agent will later branch on.

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

## Using the endpoint

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

## Testing

```bash
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm   # needed for the NER / endpoint tests
pytest
```

## Repository layout

```
app/
  main.py            FastAPI app (/health, /extract)
  config.py          settings (pydantic-settings)
  api/routes/        HTTP routes
  schemas/           Pydantic models (incl. the provenance model)
  extraction/        ioc.py · ner.py · provenance.py · service.py   <- implemented
  ingestion/         placeholder (later: PDF/HTML -> text)
  classification/    placeholder (Week 1: ATT&CK-for-ICS mapping)
  triage/            placeholder (Week 2: severity cascade + clarification branch)
  orchestration/     placeholder (Week 2: LangGraph agent graph + trace)
data/
  gazetteers/        curated threat-actor / ICS-vendor / sector lists
  samples/           sample report text (synthetic seed + your real reports)
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
  `flag_for_review` branch becomes real agent behaviour in Week 2.

## Roadmap

- **Week 1** — Extraction + classification as a plain pipeline; Phase-1 R&D bake-off
  (embeddings vs LLM-only vs hybrid) to pick the ATT&CK-for-ICS mapping method.
- **Week 2** — Wrap in LangGraph: the extraction agent's review-flagging and the triage
  agent's *clarification-vs-guess* branch (the core agentic decision), plus an agent
  trace log.
- **Week 3** — React frontend (advisory + agent trace side by side), scale evaluation to
  ~25 reports, and the writeup (precision/recall, ranking-agreement, limitations).
```
