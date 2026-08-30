# Phase 1 R&D — Classification method bake-off

One-off exploratory tooling, **not** shipped app code. This directory answers a single
question that gates the real `app/classification/` build: **which method should map
extracted attacker-behaviour text to MITRE ATT&CK for ICS techniques?**

Three notebooks, sharing one foundation:

- [`classification_bakeoff.ipynb`](classification_bakeoff.ipynb) — the rigorous 4-way
  method comparison (the main deliverable).
- [`classification_improvements.ipynb`](classification_improvements.ipynb) — isolated
  tuning ablations (embedding model, corpus representation, reranker model, LLM
  size/prompt, retrieval-window size) on the *same* eval set and metrics, one variable
  changed at a time.
- [`classification_frontier_arbiter.ipynb`](classification_frontier_arbiter.ipynb) —
  Method E: a frontier LLM reasons over Method D's own retrieved+reranked candidates
  (ACH-style evidence for/against each), instead of ranking from scratch. See "Frontier
  LLM as arbiter" below.

## Why v2 — a foundation rebuild, not just a tuning pass

An earlier version of this notebook compared methods on 10-16 hand-written examples
using a fixed `top_k=3` set-precision/recall metric. Both were foundation problems, not
tuning problems:

1. **The metric was unfair and self-capping.** Forcing every method to emit exactly 3
   predictions caps a *perfect* method's precision well below 1.0 whenever a report has
   fewer than 3 true labels, while methods emitting a variable count could still hit
   1.0 — an apples-to-oranges comparison. **Fixed:** rank-based metrics (MRR, MAP,
   Recall@k) that score a method's full ranking, no forced cutoff — and match the real
   task (a ranked shortlist for a human analyst).
2. **The dataset was far too small** to rank methods reliably, and the original
   conclusion was drawn on synthetic text that structurally favoured embeddings (it
   echoed technique names verbatim). **Fixed:** the primary eval set is now ~238 real,
   MITRE-documented procedure examples (Sandworm/Ukraine, Triton, PIPEDREAM, KillDisk…),
   mined from the same STIX bundle this project already downloads — genuine,
   citation-backed attacker behaviour at a scale no hand-written set can match.
3. **Two notebooks ran on two different datasets**, making "did this change actually
   help" unanswerable. **Fixed:** both notebooks now load the identical eval set via
   `lib/eval_data.py` and use the identical stratified sample (same seed), so
   comparisons across notebooks are apples-to-apples.

Four methods are compared, all scored identically:

- **A — Embeddings only**: cosine similarity, behaviour text vs. every technique
  description.
- **B — LLM only**: a local LLM ranks the full 79-technique catalogue directly (no
  retrieval).
- **C — Hybrid**: embeddings retrieve top-N candidates; the LLM ranks among just those.
- **D — Retrieve + rerank**: same retrieval, but a small cross-encoder reranker (no
  LLM) re-orders the candidates instead.
- **E — Frontier-LLM arbiter**: same retrieval+rerank as D, but a frontier LLM (via
  `opencode_client`, not the local Ollama model) reasons over D's own top-K candidates —
  weighing evidence for/against each ([Analysis of Competing
  Hypotheses](https://en.wikipedia.org/wiki/Analysis_of_competing_hypotheses)-style) —
  instead of ranking the full catalogue from scratch. See below.

## Fully local — no cloud APIs

- **LLM steps** run on [Ollama](https://ollama.com) (default model `qwen2.5:7b`, a
  fast instruct model — larger "thinking" models like `qwen3.5:9b` were far slower and
  *less* reliable at strict JSON in earlier testing) at `http://localhost:11434`. Zero
  API cost, offline, reproducible.
- **Structured output**: LLM calls use `ollama_client.classify_structured`, which passes
  a JSON *schema* constraining `technique_id` to an enum of valid IDs — hallucinated
  IDs are structurally impossible, not just discouraged — and forces exactly
  `LLM_RANK_SIZE` ranked predictions (fixes an earlier under-prediction problem).
- **Frontier-LLM client**: `opencode_client` shells out to the `opencode` CLI
  (`opencode run`, NDJSON output parsed) instead of the local Ollama daemon — the only
  working entry point for the flat-rate `opencode-go` plan (the raw HTTP completions
  endpoint returns `401 Insufficient balance` when called directly). The prompt is sent
  as an attached file (`-f <path>`), not as the `run` argument — a real prompt routinely
  exceeds `cmd.exe`'s ~8191-char command-line limit on Windows (`npx` always resolves to
  `npx.cmd`, always run through `cmd.exe`), which failed silently as an empty reply
  until traced to the actual subprocess exit code. It deliberately has **no**
  schema-constrained mode — the CLI exposes no grammar-constrained decoding, so unlike
  `ollama_client.classify_structured` it only emits free-form JSON with one corrective
  retry.
- **Embeddings** run locally via [`fastembed`](https://github.com/qdrant/fastembed)
  (ONNX runtime; default `BAAI/bge-base-en-v1.5`) — chosen over `sentence-transformers`
  because the latter pulls in PyTorch, whose deeply-nested license files overflow
  Windows' 260-char path limit under this project's long OneDrive path.
- **Reranking** also runs via `fastembed`'s ONNX cross-encoders (default
  `Xenova/ms-marco-MiniLM-L-6-v2`).
- **Response cache**: `data/.llm_cache.json` (gitignored) keys on hash(model + prompt +
  format), so re-running a notebook — or resuming after an interruption — is fast and
  never repeats a completed call. `classification_frontier_arbiter.ipynb` uses its own
  `data/.llm_cache_frontier_arbiter.json` (also gitignored) rather than sharing this
  file — keeps a bad run in one notebook from ever poisoning the other's cached results,
  and the `model` field in the cache key already lets several models' entries coexist
  safely if this notebook is re-run against more than one.

Honest caveats, stated in both notebooks too: a small local model is weaker at
structured reasoning than a frontier model, so LLM-based results here are a floor, not
a ceiling; and no ICS-domain-specific embedding/reranker model exists via `fastembed` —
`bge`/`ms-marco` are general-purpose web-search models, a real ceiling on A and D.

## Frontier LLM as arbiter (Method E)

A frontier LLM ranking the full 79-technique catalogue from scratch was **not** tried —
external evidence (a 2026 study evaluating open-source LLMs 8B–236B params on ATT&CK
classification) found that shape weak even at 236B params (micro-F1 0.22), with
retrieval grounding — not prompt tuning — the one lever that helped. So Method E instead
gives the frontier model Method D's own top-6 retrieved+reranked candidates and asks it
to weigh evidence for/against each (ACH-style) rather than pick from the full corpus.

First run, `opencode-go/qwen3.8-max`, same 50-example stratified sample for both methods:

| method | MRR | MAP | Recall@1 | Recall@3 |
|---|---|---|---|---|
| D: Retrieve+rerank | 0.508 | 0.51 | 0.42 | 0.58 |
| E: ACH arbiter | **0.640** | **0.64** | **0.61** | **0.66** |

0 hallucinated IDs across 50 calls (structurally bounded to the 6 offered candidates),
2/50 parse failures. A real, meaningful margin — but n=50 is one stratified sample from
one model; not yet re-run at full scale or against a second model to check the margin
holds up.

## How to run

1. Ensure Ollama is running and the models are pulled:
   ```bash
   ollama list                  # confirm qwen2.5:7b and qwen2.5:3b are present
   ollama pull qwen2.5:7b       # if not (improvements notebook also uses qwen2.5:3b)
   ```
2. Install the research deps into the project `.venv`:
   ```bash
   pip install -r research/requirements-research.txt
   ```
3. Open `classification_bakeoff.ipynb` with `research/` as the working directory
   (VS Code's notebook UI does this automatically, or launch `jupyter lab` from here),
   then **Restart & Run All**. Run `classification_improvements.ipynb` the same way
   afterward — it reuses the same cached data.

First run fetches the MITRE ATT&CK-for-ICS STIX bundle twice (once for the technique
corpus, once for procedure examples — see `lib/attack_data.py`) and caches both to
`data/`; later runs are fully offline.

## Evaluation dataset

Three sources, unified by `lib/eval_data.py`, each tagged with a `slice`:

- **`procedure`** (primary, ~238 examples) — real MITRE-documented examples of a
  technique in use, extracted from the STIX bundle's `uses` relationships. Cached at
  `data/procedure_examples.jsonl` (committed — derived from public MITRE data).
- **`synthetic-easy` / `synthetic-hard`** (~16 examples) — the original hand-written
  examples in `data/labeled_dataset.jsonl` (committed), split by whether their wording
  echoes technique names.
- **`real`** (optional, additive) — your own excerpts in the gitignored
  `data/labeled_dataset.local.jsonl` (schema in `labeled_dataset.local.jsonl.example`).
  Real report text is kept out of git, consistent with
  [`../data/samples/README.md`](../data/samples/README.md).

Every example also gets a data-driven `name_absent` flag: True when none of its true
techniques' names appear verbatim in its behaviour text — the fairest lens for "is a
method winning on lexical overlap or genuine understanding," and a large-scale
replacement for the hand-labeled easy/hard split.

**Leakage guard:** the embedded technique *corpus* is name/tactics/description only;
eval text is never added to it. Checked programmatically
(`eval_data.assert_no_leakage`), not just asserted in prose.

## Attribution

Technique reference data and procedure examples © The MITRE Corporation, from the
public [mitre-attack/attack-stix-data](https://github.com/mitre-attack/attack-stix-data)
repository (ATT&CK for ICS). MITRE ATT&CK® is a registered trademark of The MITRE
Corporation.
