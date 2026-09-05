from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class QuestionnaireIn(BaseModel):
    citizenship: str = Field(min_length=2, max_length=64)
    second_citizenship: bool = False
    second_citizenship_code: str | None = None
    age_band: str = Field(default="adult", pattern="^(minor|adult)$")
    visa_regime_id: str | None = None
    purpose: str = Field(default="tourism", pattern="^(tourism|work|study|family|other)$")
    planned_stay_days: int | None = Field(default=None, ge=1, le=3660)
    planned_entry_date: date | None = None
    eaeu_member: bool = False
    invitation: bool = False
    host_type: str | None = Field(default=None, pattern="^(individual|org|none)$")
    region_code: str | None = Field(default=None, max_length=32)
    special_statuses: list[str] = Field(default_factory=list, max_length=20)
    plans_extension_or_change: bool = False
    timezone: str = "Europe/Moscow"
    draft_consent: bool = False


class DraftResponse(BaseModel):
    draft_id: UUID
    message: str


class EvaluateResponse(BaseModel):
    snapshot_id: UUID
    pack_version: str
    disclaimer: str
    unknown_case: bool
    activated_rule_ids: list[str]
    freshness_blocked_rules: list[str]
    stages: dict[str, list[dict[str, Any]]]
    questionnaire: dict[str, Any]
    recommended_forms: list[dict[str, Any]] = Field(default_factory=list)
    reviewed_at: str | None = None


class VisaRegimeOut(BaseModel):
    id: str
    label: str
    source_slug: str
