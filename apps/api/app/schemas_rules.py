from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RuleMetaOut(BaseModel):
    rule_id: str
    version: str
    severity: str
    severity_rationale: str
    result_kind: str
    required_facts: list[str]
    official_sources: list[str]
    reviewer: str


class RegistryOut(BaseModel):
    registry_version: str
    rules: list[RuleMetaOut]


class RuleHitOut(BaseModel):
    origin: str = "rule_engine"
    rule_id: str
    rule_version: str
    result_kind: str
    severity: str
    severity_rationale: str
    message: str
    uncertainty: str
    citations: list[dict[str, Any]]
    basis_fact_keys: list[str]
    official_sources: list[str]


class AnalysisRuleHitOut(RuleHitOut):
    pass


class RunRulesRequest(BaseModel):
    document_id: UUID
    document_type: str = "contract.other"
    facts: list[dict[str, Any]] = Field(default_factory=list)
    analysis_run_id: UUID | None = None


class RunRulesResponse(BaseModel):
    document_id: UUID
    rule_results: list[RuleHitOut]
    model_findings: list[dict[str, Any]] = Field(default_factory=list)


class CompareRequest(BaseModel):
    left_document_id: UUID
    right_document_id: UUID
    left: dict[str, Any] | None = None
    right: dict[str, Any] | None = None


class CompareDocumentsRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=2, max_length=8)


class ExportRunRequest(BaseModel):
    analysis_run_id: UUID
    format: str = Field(default="json", pattern="^(json|pdf)$")


class DiffItemOut(BaseModel):
    change: str
    path: str
    left_citation: dict[str, Any] | None
    right_citation: dict[str, Any] | None
    left_text: str | None
    right_text: str | None


class CompareResponse(BaseModel):
    left_document_id: UUID
    right_document_id: UUID
    party_diffs: list[DiffItemOut]
    section_diffs: list[DiffItemOut]
    clause_diffs: list[DiffItemOut]
    refused: bool = False
    refusal_reason: str | None = None


class ExportReportRequest(BaseModel):
    document_id: UUID
    analysis_run_id: UUID | None = None
    facts: list[dict[str, Any]] = Field(default_factory=list)
    document_type: str = "contract.other"
    unanalyzed_pages: list[int] = Field(default_factory=list)
    format: str = Field(default="json", pattern="^(json|pdf)$")


class FeedbackRequest(BaseModel):
    target_type: str = Field(pattern="^(finding|rule_hit|report)$")
    target_id: str
    kind: str = Field(pattern="^(useful|error|bad_citation)$")
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: UUID
    message: str
    mutates_results: bool = False
