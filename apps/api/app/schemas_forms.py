from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FormRegisterRequest(BaseModel):
    slug: str = Field(min_length=3, max_length=128)
    title: str = Field(min_length=3, max_length=512)
    organ: str = Field(min_length=2, max_length=256)
    purpose: str = Field(min_length=2, max_length=128)
    region: str = Field(default="RF", max_length=32)
    authority: str = Field(min_length=2, max_length=256)
    source_snapshot_id: UUID
    raw_base64: str = Field(min_length=1)
    content_sha256: str = Field(min_length=64, max_length=64)
    act_number: str
    act_date: date
    act_title: str
    valid_from: date
    valid_to: date | None = None
    reviewed_at: datetime
    reviewer: str = Field(min_length=2, max_length=128)
    warning: str | None = None


class FormCardOut(BaseModel):
    id: str
    slug: str
    title: str
    organ: str
    purpose: str
    region: str
    authority: str
    status: str
    edition: str
    act_number: str | None
    act_date: str | None
    act_title: str | None
    valid_from: str | None
    valid_to: str | None
    reviewed_at: str | None
    reviewer: str | None
    content_sha256: str | None
    source: dict[str, Any] | None
    warning: str
    has_raw: bool
    category: str = "entry_stay"
    category_label: str = ""
    form_kind: str = "government_form"
    fill_ready: bool = False
    fill_version_id: str | None = None
    unavailable_reason: str | None = None
    official_url: str | None = None
    appendix: str | None = None
    unified_official_form: bool | None = None
    worksheet_ready: bool = False


class AbuseReportRequest(BaseModel):
    target_type: str = Field(pattern="^(form|source|medical_org|medical_procedure)$")
    target_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(pattern="^(outdated|incorrect|abuse|other)$")
    comment: str = Field(default="", max_length=2000)


class AbuseReportResponse(BaseModel):
    id: UUID
    message: str


class MedicalPdfRequest(BaseModel):
    kind: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    body_lines: list[str] = Field(default_factory=list, max_length=100)
    answers: dict[str, str] = Field(default_factory=dict)


class MedicalOrgRegisterRequest(BaseModel):
    name: str
    region_code: str
    source_snapshot_id: UUID
    valid_from: date
    valid_to: date | None = None


class MedicalProcedureRegisterRequest(BaseModel):
    slug: str
    title: str
    explanation: str
    applicable_to: str
    deadline_text: str
    source_snapshot_id: UUID
    checklist: list[str] = Field(default_factory=list)
    questionnaire_fields: list[str] = Field(default_factory=list)


class FillPreviewRequest(BaseModel):
    form_version_id: UUID
    answers: dict[str, str] = Field(default_factory=dict)


class FillGenerateRequest(BaseModel):
    form_version_id: UUID
    answers: dict[str, str] = Field(default_factory=dict)
    catalog_form_id: UUID | None = None


class FillDraftSaveRequest(BaseModel):
    catalog_form_id: UUID
    answers: dict[str, str] = Field(default_factory=dict)


class FillPreDownloadRequest(BaseModel):
    form_version_id: UUID
    answers: dict[str, str] = Field(default_factory=dict)


class CoordMapSubmitRequest(BaseModel):
    form_version_id: UUID
    map_json: str
    author_id: str = Field(min_length=2, max_length=128)


class CoordMapApproveRequest(BaseModel):
    draft_id: UUID
    reviewer_id: str = Field(min_length=2, max_length=128)
