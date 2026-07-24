"""Shared pytest fixtures and helpers.

IOC tests are pure regex and always run. NER / endpoint tests need the spaCy model;
they are skipped (not failed) if ``en_core_web_sm`` is not installed, so the suite is
still useful on a fresh checkout without the model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_ROOT = Path(__file__).resolve().parents[1]


def _model_available() -> bool:
    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


MODEL_AVAILABLE = _model_available()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_text() -> str:
    return (_ROOT / "data" / "samples" / "sample_advisory_01.txt").read_text(encoding="utf-8")
