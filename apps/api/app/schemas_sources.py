from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SeedResponse(BaseModel):
    created: int
    allowlist_version: str


class SourceOut(BaseModel):
    id: UUID
    slug: str
    title: str
    organ: str
    official_url: str
    host: str
    state: str
    criticality: str


class SnapshotOut(BaseModel):
    id: UUID
    source_id: UUID
    state: str
    content_hash: str
    final_url: str
    fetched_at: str
    parser_version: str
    link_status: str
    reviewer_id: str | None = None
    review_comment: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    act_title: str | None = None
    act_number: str | None = None
    act_date: date | None = None


class ReviewDecision(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)
    valid_from: date | None = None
    valid_to: date | None = None
    act_title: str | None = None
    act_number: str | None = None
    act_date: date | None = None


class CitationRequest(BaseModel):
    snapshot_id: UUID
    quote: str = Field(min_length=1, max_length=2000)
    on_date: date


class CitationResponse(BaseModel):
    payload: dict[str, Any]


class DiffOut(BaseModel):
    diff: dict[str, Any]


class AuditOut(BaseModel):
    id: UUID
    at: str
    actor: str
    action: str
    source_id: UUID | None
    snapshot_id: UUID | None
    detail: dict[str, Any]


class ReviewTaskOut(BaseModel):
    id: UUID
    source_id: UUID
    snapshot_id: UUID
    reason: str
    status: str
    created_at: str
