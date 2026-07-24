# Sample reports

Plain-text threat reports used to demo and test the extraction endpoint.

## Format
- One report per `.txt` file, UTF-8, plain text (already extracted from PDF/HTML).
- The endpoint takes raw text in the request body; ingestion (PDF/HTML → text) is a
  later module, so for now paste/clean report text into a `.txt` file here.

## What's here
- `sample_advisory_01.txt` — a **synthetic** CISA-style ICS advisory. It is fabricated
  for demoing (note the `SYNTHETIC SAMPLE` marker and `ICSA-26-XXX-01` id) and
  deliberately includes defanged indicators, a threat actor, ICS vendors, a CVE, and a
  SHA-256 so the extractor has something to find.

## Adding real reports
Drop real CISA ICS-CERT advisories or Dragos public OT reports here as `.txt` files,
e.g. `icsa-24-123-01.txt`. Then run them through the endpoint:

```bash
# PowerShell
$body = @{ text = (Get-Content -Raw data/samples/icsa-24-123-01.txt); report_id = "icsa-24-123-01" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/extract -ContentType application/json -Body $body
```

Real report text is not committed here to avoid redistributing third-party content;
keep your own copies locally.
