"""Shared pytest fixtures and helpers.

IOC tests are pure regex and always run. NER / endpoint tests need the spaCy model;
they are skipped (not failed) if ``en_core_web_sm`` is not installed, so the suite is
still useful on a fresh checkout without the model. Classification tests need the
fastembed embedding/reranker models and are skipped the same way.
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


def _fastembed_available() -> bool:
    try:
        from app.classification.retrieval import get_embedder

        get_embedder()
        return True
    except Exception:
        return False


MODEL_AVAILABLE = _model_available()
FASTEMBED_AVAILABLE = _fastembed_available()
PIPELINE_AVAILABLE = MODEL_AVAILABLE and FASTEMBED_AVAILABLE


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_text() -> str:
    return (_ROOT / "data" / "samples" / "sample_advisory_01.txt").read_text(encoding="utf-8")
