"""Unit tests for behaviour segmentation (pure regex + spacy.blank sentencizer, no
downloaded model -- runs unconditionally like the triage signal tests).

Each test below locks in a real bug found and fixed this session: running the
*previous* segmentation on the bundled sample advisory produced a section header
glued to the following sentence (spaCy's sentencizer doesn't split on newlines), so
mitigation advice and an affected-products list were being handed to the classifier as
if they were attacker behaviour, and a "not confirmed vulnerable" sentence was
confidently matched to a technique.
"""

from __future__ import annotations

from pathlib import Path

from app.classification import segmentation

_SAMPLE_TEXT = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "samples"
    / "sample_advisory_01.txt"
).read_text(encoding="utf-8")


def _texts(segments: list[segmentation.Segment]) -> list[str]:
    return [s.text for s in segments]


def test_mitigations_section_is_fully_suppressed():
    segments = _texts(segmentation.segment(_SAMPLE_TEXT))
    assert not any("Operators should remove PLC" in t for t in segments)
    assert not any("Known Exploited Vulnerabilities" in t for t in segments)


def test_affected_products_section_is_fully_suppressed():
    segments = _texts(segmentation.segment(_SAMPLE_TEXT))
    assert not any("Modicon M340 and M580" in t for t in segments)


def test_negated_not_confirmed_vulnerable_is_dropped():
    # Belt-and-suspenders: this sentence lives inside the suppressed AFFECTED PRODUCTS
    # section already, but the negation guard must also catch it standalone, since a
    # real report could phrase a non-affected claim outside a labeled section.
    segments = segmentation.segment(
        "TECHNICAL DETAILS\nRockwell Automation ControlLogix devices were assessed "
        "but not confirmed vulnerable to this issue."
    )
    assert segments == []


def test_document_title_is_not_classified_as_behaviour():
    segments = _texts(segmentation.segment(_SAMPLE_TEXT))
    assert not any("ICS Advisory (SYNTHETIC SAMPLE)" in t for t in segments)
    assert not any("Improper Authentication" in t for t in segments)


def test_header_glued_to_body_no_longer_survives_as_one_unit():
    # The original bug: a section header on its own line gets glued by the
    # sentencizer to the sentence after it, so ".isupper()" never fires because the
    # combined string isn't all-caps.
    segments = _texts(
        segmentation.segment(
            "SUMMARY\nAn attacker exploited a known vulnerability to gain unauthorized "
            "remote access to the control network."
        )
    )
    assert len(segments) == 1
    assert not segments[0].startswith("SUMMARY")
    assert segments[0].startswith("An attacker exploited")


def test_real_behaviour_sentences_survive():
    segments = _texts(segmentation.segment(_SAMPLE_TEXT))
    assert any("CVE-2026-2841" in t and "CVSS" in t for t in segments)
    assert any("VOLTZITE" in t for t in segments)
    assert any("lateral movement" in t for t in segments)


def test_offsets_round_trip_to_the_original_text():
    for seg in segmentation.segment(_SAMPLE_TEXT):
        assert _SAMPLE_TEXT[seg.start : seg.end] == seg.text


def test_line_wrapped_body_sentence_is_not_mistaken_for_a_header():
    # A paragraph hard-wrapped at ~80 chars can have a first physical line that is
    # short and, mid-sentence, lacks terminal punctuation -- this must not be treated
    # as a header (it isn't ALL-CAPS, which is the only signal used for header lines).
    text = (
        "TECHNICAL DETAILS\n"
        "Analysts observed the actor staging payloads from the command-and-control "
        "domain\nexample[.]net and beaconing to a remote host over port 443."
    )
    segments = _texts(segmentation.segment(text))
    assert len(segments) == 1
    assert segments[0].startswith("Analysts observed")
    assert "domain" in segments[0] and "beaconing" in segments[0]


def test_blank_input_returns_no_segments():
    assert segmentation.segment("") == []
    assert segmentation.segment("   \n\n   ") == []
