"""Thin OpenCode CLI wrapper for the LLM-only and hybrid methods.

Mirrors ``research/lib/ollama_client.py``'s calling convention, but instead of talking
to a local Ollama daemon it shells out to the ``opencode`` CLI (``opencode run``),
which is the only working entry point for the flat-rate ``opencode-go`` plan — the raw
HTTP completions endpoint returns ``401 Insufficient balance`` when called directly.

``opencode run --format json`` prints one JSON object per line (NDJSON): a ``text``
part's ``part.text`` holds a chunk of the model's reply, in order. There is no
grammar-constrained decoding available through the CLI, so unlike
``ollama_client.classify_structured()`` there is no ``classify_structured()`` here —
only the free-form-JSON-plus-retry mode, reusing :func:`ollama_client.parse_prediction`
for the actual parsing so hallucination/parse-failure handling stays identical.

The prompt is sent as an attached file (``opencode run <short message> -f <path>``),
not as the ``run`` positional argument — a real prompt (e.g. an ACH arbiter prompt with
several candidates' full descriptions) routinely exceeds ~8000 chars, and `npx` resolves
to `npx.cmd` on Windows, which is always executed through `cmd.exe` regardless of
`shell=True` — hitting cmd.exe's ~8191-char command-line limit ("The command line is
too long", exit code 1). `_run_opencode` used to pass the prompt directly as an argv
element and silently returned "" on that failure, which looked identical to a genuine
LLM parse failure until traced to the actual subprocess error.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from research.lib.ollama_client import LLMPrediction, ResponseCache, parse_prediction

DEFAULT_OPENCODE_VERSION = "opencode-ai@1.18.21"
_ATTACHED_PROMPT_MESSAGE = "Follow the instructions in the attached file precisely and reply with only the required JSON."

# On Windows, subprocess.run(["npx", ...]) fails with FileNotFoundError because npx
# resolves to npx.cmd, which CreateProcess won't launch without shell resolution.
# shutil.which() resolves the real executable so list-form args (no shell=True) still work.
_NPX = shutil.which("npx") or "npx"


def _cacheable(result: LLMPrediction) -> dict:
    """Fields needed to reconstruct an LLMPrediction, excluding `from_cache` itself."""
    data = vars(result).copy()
    data.pop("from_cache", None)
    return data


def _run_opencode(prompt: str, model: str, timeout: int = 120) -> str:
    """Run one ``opencode run`` call and return the concatenated text reply.

    The prompt is written to a temp file and attached via ``-f`` rather than passed on
    the command line — see the module docstring for why.

    Returns ``""`` on timeout, non-zero exit, or a response with no text parts — the
    caller treats an empty string as a parse failure, same as a malformed reply.
    """
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="opencode_prompt_", text=True)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(prompt)
        try:
            proc = subprocess.run(
                [
                    _NPX, DEFAULT_OPENCODE_VERSION, "run", _ATTACHED_PROMPT_MESSAGE,
                    "-f", path, "-m", model, "--format", "json",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ""
    finally:
        Path(path).unlink(missing_ok=True)

    if proc.returncode != 0:
        return ""

    chunks: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part", {})
        if event.get("type") == "text" and part.get("type") == "text":
            chunks.append(part.get("text", ""))

    return "".join(chunks)


def ping(model: str, timeout: int = 60) -> str:
    """Trivial round-trip so a misconfigured model fails loudly and early."""
    reply = _run_opencode("Reply with exactly one word: ready", model, timeout=timeout)
    if not reply:
        raise RuntimeError(f"opencode run produced no reply for model {model!r}")
    return reply.strip()


def classify(
    model: str,
    prompt: str,
    valid_ids: set[str],
    cache: ResponseCache | None = None,
    timeout: int = 120,
) -> LLMPrediction:
    """Ask ``model`` to classify (free-form JSON mode), retrying once on parse failure."""
    cached = cache.get(model, prompt, "opencode-json") if cache is not None else None
    if cached is not None:
        return LLMPrediction(**cached, from_cache=True)

    current_prompt = prompt
    raw_text = ""

    for attempt in (1, 2):
        raw_text = _run_opencode(current_prompt, model, timeout=timeout)
        ranked, hallucinated = parse_prediction(raw_text, valid_ids)
        if ranked is not None:
            result = LLMPrediction(
                ranked_ids=ranked,
                parse_failure=False,
                raw_text=raw_text,
                attempts=attempt,
                hallucinated=hallucinated,
            )
            if cache is not None:
                cache.set(model, prompt, "opencode-json", _cacheable(result))
            return result
        # Feed the bad output back and ask for a correction before the second attempt.
        current_prompt = (
            f"{prompt}\n\nYour previous reply was not valid JSON in the required shape:\n"
            f"{raw_text}\n\nReply with ONLY a JSON object like "
            '{"predicted_techniques": [{"technique_id": "TXXXX", "rank": 1}]} and nothing else.'
        )

    result = LLMPrediction(
        ranked_ids=[], parse_failure=True, raw_text=raw_text, attempts=2, hallucinated=[]
    )
    if cache is not None:
        cache.set(model, prompt, "opencode-json", _cacheable(result))
    return result
