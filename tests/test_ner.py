"""Tests for gazetteer + spaCy entity extraction (requires en_core_web_sm)."""

from __future__ import annotations

import pytest

from app.extraction.ner import extract_entities
from tests.conftest import MODEL_AVAILABLE

pytestmark = pytest.mark.skipif(
    not MODEL_AVAILABLE, reason="spaCy model en_core_web_sm not installed"
)


def _texts(entities, ent_type):
    return [e.text for e in entities if e.type == ent_type]


def test_gazetteer_threat_actors():
    ents = extract_entities("Activity attributed to VOLTZITE, overlapping ELECTRUM tooling.")
    actors = _texts(ents, "threat_actor")
    assert "VOLTZITE" in actors
    assert "ELECTRUM" in actors
    assert all(e.method == "gazetteer" for e in ents if e.type == "threat_actor")


def test_gazetteer_vendor():
    ents = extract_entities("Affected: Schneider Electric Modicon controllers.")
    assert "Schneider Electric" in _texts(ents, "ics_vendor")


def test_longest_sector_match_wins():
    ents = extract_entities("Targeting the water and wastewater sector.")
    sectors = _texts(ents, "sector")
    assert "water and wastewater" in sectors
    # The sub-span "water" must not also appear as a separate overlapping entity.
    assert "water" not in sectors


def test_every_entity_has_offsets():
    text = "VOLTZITE targeted Siemens equipment."
    for e in extract_entities(text):
        assert text[e.start : e.end] == e.text
