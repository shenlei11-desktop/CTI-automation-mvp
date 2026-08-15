# CTI/ICS Triage Tool

Agent-assisted cyber threat intelligence (CTI) triage for **OT/ICS** (operational
technology / industrial control systems) threat reports. It turns a raw threat report —
a CISA ICS-CERT advisory or a Dragos public OT report — into a structured,
severity-ranked security advisory, automating the tedious, high-volume parts of triage
while keeping the *judgment* (severity scoring especially) as interpretable rules rather
than a black-box model.

> **Status: extraction + triage working.** Classification and LangGraph orchestration
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
  main.py            FastAPI app (/health, /extract, /triage)
  config.py          settings (pydantic-settings)
  api/routes/        HTTP routes
  schemas/           Pydantic models (incl. the provenance model)
  extraction/        ioc.py · ner.py · provenance.py · service.py   <- implemented
  triage/            signals.py · kev.py · cascade.py · service.py  <- implemented
  ingestion/         placeholder (later: PDF/HTML -> text)
  classification/    placeholder (next: ATT&CK-for-ICS mapping, Phase-1 R&D bake-off done)
  orchestration/     placeholder (next: LangGraph agent graph + trace)
data/
  gazetteers/        curated threat-actor / ICS-vendor / sector lists
  triage/            curated exposure / asset-criticality-tier keyword lists
  kev/               committed CISA Known Exploited Vulnerabilities snapshot
  samples/           sample report text (synthetic seed + your real reports)
research/            Phase-1 R&D: classification method bake-off + confidence calibration
tests/               pytest unit + endpoint tests
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
- **The quality summary is a metric, not yet a decision.** The `proceed` /
  `flag_for_review` branch becomes real agent behaviour once orchestration exists.
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

## Roadmap

- ~~Extraction + triage: a fully-traceable severity cascade with the
  clarification-vs-guess branch (the core agentic decision).~~ **Done.**
- ~~Classification: Phase-1 R&D bake-off to pick the ATT&CK-for-ICS mapping method.~~
  **Done** (see [`research/`](research/)) — implementation is a parallel branch.
- **Next** — LangGraph orchestration wrapping extraction → classification → triage,
  with an agent trace log.
- **Later** — React frontend (advisory + agent trace side by side), scale evaluation to
  ~25 reports, and the writeup (precision/recall, ranking-agreement, limitations).
```
