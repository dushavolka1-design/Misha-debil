from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas_rules import RuleHitOut


class RetryAnalysisRequest(BaseModel):
    stage: str = Field(default="analysis", description="Этап для повтора: analysis, ocr, extracting")


class StartAnalysisRequest(BaseModel):
    document_id: UUID
    fixture_id: str | None = Field(
        default=None,
        description="Golden fixture id for deterministic local/test runs",
    )


class StartAnalysisResponse(BaseModel):
    run_id: UUID
    status: str
    pipeline_version: str
    prompt_version: str
    schema_version: str


class ProgressEventOut(BaseModel):
    stage: str
    percent: int
    page: int | None = None
    error_code: str | None = None
    at: str


class CitationOut(BaseModel):
    page: int
    bbox: dict[str, float]
    quote: str


class FindingOut(BaseModel):
    id: UUID
    kind: str
    entity_type: str
    raw_text: str
    normalized_value: Any
    confidence: float
    uncertainty_state: str
    citation: CitationOut


class PageOut(BaseModel):
    page_number: int
    width: float
    height: float
    rotation: int
    confidence: float
    language: str
    source: str
    error_code: str | None = None
    layout_region_types: list[str]


class AnalysisRunOut(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    pipeline_version: str
    prompt_version: str
    schema_version: str
    ocr_provider: str
    ocr_model_version: str
    llm_provider: str
    llm_model_version: str
    llm_available: bool = False
    local_steps: list[str] = Field(default_factory=list)
    error_code: str | None
    created_at: datetime
    progress: list[ProgressEventOut]
    pages: list[PageOut]
    findings: list[FindingOut]
    rule_hits: list[RuleHitOut] = Field(default_factory=list)
    rejected_llm_count: int
