"""Behaviour segmentation for ``classify_text()`` -- turns whole-report text into
sentence-level candidate behaviours.

Fixes a real bug in the previous inline approach: ``prov.build_sentence_index`` uses
spaCy's rule-based sentencizer, which does not split on line breaks, so a section
header on its own line (e.g. "MITIGATIONS") gets glued onto the sentence that follows
it ("MITIGATIONS\\nOperators should..."). A naive ``.isupper()`` check on the resulting
sentence never fires, because the sentence isn't all-caps once body text is attached --
so mitigation advice, an affected-products list, and even negated claims ("assessed but
not confirmed vulnerable") were being handed to the classifier as if they were attacker
behaviour, and confidently matched to unrelated techniques.

This module splits on blank lines *before* sentence-splitting, so a header line is
never glued to anything, then strips it, tracks which section it belongs to, and skips
non-behaviour sections and negated claims entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.extraction import provenance as prov

# A block this short with no full stop anywhere in it is almost certainly a title, not
# wrapped prose -- real narrative sentences virtually always contain a period. Used
# only for the document's very first block, to catch a mixed-case title/subtitle line
# ("ICS Advisory ... \n Schneider Electric Modicon PLC - Improper Authentication")
# that isn't ALL-CAPS and so isn't caught by the header check below. Deliberately not
# applied to every block: a plain-text report hard-wrapped at ~80 chars produces many
# body lines that are short and, mid-sentence, punctuation-free -- checking "is this
# physical line short" anywhere but the title would misfire constantly on wrapped body
# text and silently drop or misclassify real content.
_TITLE_BLOCK_MAX_LENGTH = 200

# Sections that describe the fix, the affected inventory, or metadata -- never
# attacker behaviour. Everything under one of these headers is dropped until the next
# header (matched as a prefix, so "AFFECTED PRODUCTS AND VERSIONS" still matches
# "AFFECTED PRODUCTS").
_NON_BEHAVIOR_SECTIONS = (
    "MITIGATIONS",
    "RECOMMENDATIONS",
    "AFFECTED PRODUCTS",
    "BACKGROUND",
    "CONTACT",
    "REFERENCES",
    "ACKNOWLEDGEMENTS",
    "ACKNOWLEDGMENTS",
)

# Catches "assessed but not confirmed vulnerable" -- a statement that something is
# explicitly NOT affected, previously classified as a confident technique match.
_NEGATION_RE = re.compile(
    r"\b(not|no|isn't|aren't|wasn't|weren't)\s+"
    r"(confirmed|affected|vulnerable|impacted|susceptible|exploitable)\b",
    re.IGNORECASE,
)

# Splits `text` into blank-line-separated blocks. Matches one newline, optional
# trailing whitespace, then one or more further newlines -- so multiple consecutive
# blank lines still count as a single separator.
_BLOCK_SEPARATOR_RE = re.compile(r"\n[ \t]*\n+")


@dataclass
class Segment:
    text: str
    start: int
    end: int


def _is_header_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and stripped.isupper()


def _looks_like_document_title(block_text: str) -> bool:
    stripped = block_text.strip()
    return bool(stripped) and len(stripped) <= _TITLE_BLOCK_MAX_LENGTH and "." not in stripped


def _is_non_behavior_section(header: str) -> bool:
    normalized = header.strip().upper()
    return any(normalized.startswith(section) for section in _NON_BEHAVIOR_SECTIONS)


def _is_negated(text: str) -> bool:
    return bool(_NEGATION_RE.search(text))


def _iter_blocks(text: str) -> list[tuple[str, int, int]]:
    """Split `text` into blank-line-separated blocks as (text, start, end), using
    original character offsets -- provenance must survive segmentation."""
    blocks = []
    pos = 0
    for sep in _BLOCK_SEPARATOR_RE.finditer(text):
        block = text[pos : sep.start()]
        if block.strip():
            blocks.append((block, pos, sep.start()))
        pos = sep.end()
    tail = text[pos:]
    if tail.strip():
        blocks.append((tail, pos, len(text)))
    return blocks


def _split_leading_headers(block_text: str) -> tuple[list[str], str, int]:
    """Consume leading header/title lines from a block. Returns the headers found, the
    remaining body text, and how many characters of `block_text` the headers occupied
    (including their trailing newlines), so the caller can compute offsets into the
    original text for the body that's left.
    """
    lines = block_text.split("\n")
    i = 0
    while i < len(lines) and _is_header_line(lines[i]):
        i += 1
    headers = lines[:i]
    consumed = sum(len(line) + 1 for line in headers)  # +1 per newline consumed
    body_text = "\n".join(lines[i:])
    return headers, body_text, consumed


def segment(text: str) -> list[Segment]:
    """Turn whole-report `text` into candidate behaviour segments: split on blank
    lines first, strip leading header/title lines, drop non-behaviour sections
    entirely, sentence-split what remains, and drop negated ("not affected") claims.
    """
    segments: list[Segment] = []
    current_section: str | None = None

    for index, (block_text, block_start, _block_end) in enumerate(_iter_blocks(text)):
        if index == 0 and _looks_like_document_title(block_text):
            continue

        headers, body_text, consumed = _split_leading_headers(block_text)

        if headers:
            last_header = headers[-1]
            if _is_non_behavior_section(last_header):
                current_section = last_header
                continue
            current_section = None
        elif current_section is not None:
            # A continuation paragraph of a still-open suppressed section.
            continue

        if not body_text.strip():
            continue

        body_start = block_start + consumed
        for sent in prov.build_sentence_index(body_text):
            sent_text = sent.text.strip()
            if not sent_text or sent_text.isupper() or _is_negated(sent_text):
                continue
            segments.append(
                Segment(
                    text=sent.text,
                    start=body_start + sent.start,
                    end=body_start + sent.end,
                )
            )

    return segments
