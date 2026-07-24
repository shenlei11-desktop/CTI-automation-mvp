"""Source-sentence provenance.

Every extracted fact must be traceable to the sentence it came from. We segment the
report into sentences once, then map each fact's character offset to its containing
sentence. Segmentation uses a lightweight ``spacy.blank("en")`` pipeline with only a
rule-based ``sentencizer`` — it needs no downloaded model and keeps provenance decoupled
from the (heavier) NER model.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass

import spacy
from spacy.language import Language

from app.schemas.extraction import SourceSpan


@dataclass
class Sentence:
    text: str
    start: int
    end: int


@functools.lru_cache(maxsize=1)
def _get_sentencizer() -> Language:
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def build_sentence_index(text: str) -> list[Sentence]:
    """Segment ``text`` into sentences with their character spans."""
    doc = _get_sentencizer()(text)
    return [Sentence(sent.text, sent.start_char, sent.end_char) for sent in doc.sents]


def locate(sentences: list[Sentence], start: int, end: int) -> SourceSpan:
    """Return the SourceSpan for the sentence containing offset ``start``."""
    chosen: Sentence | None = None
    for sent in sentences:
        if sent.start <= start < sent.end:
            chosen = sent
            break
        if sent.start <= start:  # track the last sentence that begins at/before start
            chosen = sent
    if chosen is None:
        chosen = sentences[0] if sentences else Sentence("", 0, 0)
    return SourceSpan(sentence=chosen.text, start=start, end=end)
