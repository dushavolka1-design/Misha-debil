from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class PageRecord:
    page_number: int
    width: float
    height: float
    rotation: int
    confidence: float
    language: str
    source: str
    text: str  # stored; never logged
    layout: list[dict[str, Any]]
    words: list[dict[str, Any]]
    error_code: str | None = None


@dataclass
class FindingRecord:
    id: UUID
    kind: str
    entity_type: str
    raw_text: str
    normalized_value: Any
    confidence: float
    uncertainty_state: str
    citation: dict[str, Any]
