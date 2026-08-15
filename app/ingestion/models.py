"""Shared building blocks for the ingestion extractors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawIngestResult:
    text: str
    title: str | None


class IngestionError(Exception):
    """Raised when a source can't be turned into text: an unreachable URL, an
    unsupported content type, or an unreadable file. Caught at the route layer and
    surfaced as a 422 with the message as-is."""
