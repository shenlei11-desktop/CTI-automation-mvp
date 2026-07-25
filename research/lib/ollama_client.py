"""Thin Ollama wrapper for the LLM-only and hybrid methods.

Two calling modes:

- :func:`classify` — free-form ``format="json"``, with a corrective retry on parse
  failure. This is the baseline mode: small local models are less reliable than
  frontier models at emitting strict JSON, so that unreliability is handled *visibly*
  (parse failures and hallucinated IDs are counted, not hidden) rather than retried
  away silently.
- :func:`classify_structured` — ``format=<json schema>`` with ``technique_id``
  constrained to an enum of the allowed IDs. Ollama's structured-output mode makes the
  model's decoding grammar-constrained, so hallucinated IDs become structurally
  impossible rather than merely rare, and malformed JSON becomes very unlikely. This is
  the improved mode.

Both modes share :func:`parse_prediction` for turning a raw response into ranked IDs,
and both can use a :class:`ResponseCache` to make repeated notebook runs fast and to
avoid losing completed calls if a run is interrupted midway.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ollama

_TECHNIQUE_ID_RE = re.compile(r"^T\d{4}$")


@dataclass
class LLMPrediction:
    ranked_ids: list[str]  # valid technique IDs, best first
    parse_failure: bool
    raw_text: str  # last raw model response (for spot-checking in the notebook)
    attempts: int
    hallucinated: list[str] = field(default_factory=list)
    from_cache: bool = False


class ResponseCache:
    """A tiny on-disk cache for LLM calls, keyed by hash(model + prompt + format).

    Makes re-running the notebook (or resuming after an interruption) fast — slow
    local-model calls only ever happen once per unique (model, prompt) pair. Writes
    through to disk after every new entry so an interrupted run doesn't lose progress.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._data: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    @staticmethod
    def _key(model: str, prompt: str, fmt: Any) -> str:
        raw = json.dumps({"model": model, "prompt": prompt, "format": fmt}, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, model: str, prompt: str, fmt: Any) -> dict[str, Any] | None:
        return self._data.get(self._key(model, prompt, fmt))

    def set(self, model: str, prompt: str, fmt: Any, value: dict[str, Any]) -> None:
        self._data[self._key(model, prompt, fmt)] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=1), encoding="utf-8")

    def __len__(self) -> int:
        return len(self._data)


def _cacheable(result: LLMPrediction) -> dict[str, Any]:
    """Fields needed to reconstruct an LLMPrediction, excluding `from_cache` itself
    (which is set fresh by the caller on load, not stored)."""
    data = vars(result).copy()
    data.pop("from_cache", None)
    return data


def list_models() -> list[str]:
    """Return the names of locally available Ollama models."""
    return [m.model for m in ollama.list().models]


def ping(model: str) -> str:
    """Trivial round-trip so a misconfigured model/daemon fails loudly and early."""
    resp = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        options={"temperature": 0.0},
    )
    return resp["message"]["content"].strip()


def _coerce_id_list(parsed: object) -> list[str] | None:
    """Pull an ordered list of technique-ID strings out of a permissive JSON shape.

    Accepts what small models actually emit: ``{"predicted_techniques": [...]}`` where
    the list holds either ``{"technique_id": "T0836", "rank": 1}`` objects or bare
    ``"T0836"`` strings, or a top-level bare list of either. Returns None if no
    plausible list is found (treated as a parse failure by the caller).
    """
    if isinstance(parsed, dict):
        for key in ("predicted_techniques", "techniques", "predictions", "results"):
            if key in parsed:
                parsed = parsed[key]
                break
        else:
            return None

    if not isinstance(parsed, list):
        return None

    items: list[tuple[int, str]] = []
    for position, entry in enumerate(parsed):
        if isinstance(entry, str):
            items.append((position, entry))
        elif isinstance(entry, dict):
            tech_id = entry.get("technique_id") or entry.get("id")
            if isinstance(tech_id, str):
                rank = entry.get("rank")
                order = rank if isinstance(rank, int) else position
                items.append((order, tech_id))
    # A validly-typed but empty list is a legitimate "no confident matches" answer,
    # not a parse failure — only the earlier returns (no usable key/not a list at all)
    # signal an actual parse failure.
    items.sort(key=lambda t: t[0])
    return [tech_id for _, tech_id in items]


def parse_prediction(
    raw_text: str, valid_ids: set[str]
) -> tuple[list[str] | None, list[str]]:
    """Parse one raw model response.

    Returns ``(ranked_valid_ids, hallucinated_ids)``; ``ranked_valid_ids`` is None when
    the text is not usable JSON (signals a parse failure to the caller).
    """
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return None, []

    raw_ids = _coerce_id_list(parsed)
    if raw_ids is None:
        return None, []

    ranked: list[str] = []
    hallucinated: list[str] = []
    seen: set[str] = set()
    for tech_id in raw_ids:
        norm = tech_id.strip().upper()
        if not _TECHNIQUE_ID_RE.match(norm) or norm in seen:
            if norm not in valid_ids and _TECHNIQUE_ID_RE.match(norm):
                hallucinated.append(norm)
            continue
        seen.add(norm)
        if norm in valid_ids:
            ranked.append(norm)
        else:
            hallucinated.append(norm)
    return ranked, hallucinated


def classify(
    model: str, prompt: str, valid_ids: set[str], cache: ResponseCache | None = None
) -> LLMPrediction:
    """Ask ``model`` to classify (free-form JSON mode), retrying once on parse failure."""
    cached = cache.get(model, prompt, "json") if cache is not None else None
    if cached is not None:
        return LLMPrediction(**cached, from_cache=True)

    messages = [{"role": "user", "content": prompt}]
    raw_text = ""

    for attempt in (1, 2):
        resp = ollama.chat(
            model=model, messages=messages, format="json", options={"temperature": 0.0}
        )
        raw_text = resp["message"]["content"]
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
                cache.set(model, prompt, "json", _cacheable(result))
            return result
        # Feed the bad output back and ask for a correction before the second attempt.
        messages += [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": (
                    "That was not valid JSON in the required shape. Reply with ONLY a "
                    'JSON object like {"predicted_techniques": [{"technique_id": '
                    '"TXXXX", "rank": 1}]} and nothing else.'
                ),
            },
        ]

    result = LLMPrediction(
        ranked_ids=[], parse_failure=True, raw_text=raw_text, attempts=2, hallucinated=[]
    )
    if cache is not None:
        cache.set(model, prompt, "json", _cacheable(result))
    return result


def build_schema(
    valid_ids: list[str], max_predictions: int, min_predictions: int | None = None
) -> dict[str, Any]:
    """A JSON Schema constraining ``technique_id`` to an enum of ``valid_ids``.

    Passed as Ollama's ``format`` — the model's decoding is grammar-constrained to this
    schema, so an ID outside ``valid_ids`` becomes structurally impossible rather than
    merely rare (hallucination-by-construction is retired, not just discouraged).
    """
    array_schema: dict[str, Any] = {
        "type": "array",
        "maxItems": max_predictions,
        "items": {
            "type": "object",
            "properties": {
                "technique_id": {"type": "string", "enum": sorted(valid_ids)},
                "rank": {"type": "integer"},
            },
            "required": ["technique_id", "rank"],
        },
    }
    if min_predictions is not None:
        array_schema["minItems"] = min_predictions

    return {
        "type": "object",
        "properties": {"predicted_techniques": array_schema},
        "required": ["predicted_techniques"],
    }


def classify_structured(
    model: str,
    prompt: str,
    valid_ids: set[str],
    max_predictions: int = 5,
    min_predictions: int | None = None,
    cache: ResponseCache | None = None,
) -> LLMPrediction:
    """Ask ``model`` to classify with a schema-constrained response (improved mode).

    No corrective retry loop is needed here — the schema makes malformed/out-of-vocab
    output structurally unlikely — but a single retry is still attempted defensively
    (e.g. the model times out or the daemon hiccups) rather than assuming perfection.
    """
    schema = build_schema(sorted(valid_ids), max_predictions, min_predictions)
    cached = cache.get(model, prompt, schema) if cache is not None else None
    if cached is not None:
        return LLMPrediction(**cached, from_cache=True)

    raw_text = ""
    for attempt in (1, 2):
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format=schema,
            options={"temperature": 0.0},
        )
        raw_text = resp["message"]["content"]
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
                cache.set(model, prompt, schema, _cacheable(result))
            return result

    result = LLMPrediction(
        ranked_ids=[], parse_failure=True, raw_text=raw_text, attempts=2, hallucinated=[]
    )
    if cache is not None:
        cache.set(model, prompt, schema, _cacheable(result))
    return result
