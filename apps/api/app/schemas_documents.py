from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UploadLimitsResponse(BaseModel):
    max_bytes: int
    max_pages: int
    allowed_extensions: list[str]
    formats_label: str


class UploadIntentRequest(BaseModel):
    display_filename: str = Field(min_length=1, max_length=512)
    content_type: str
    size_bytes: int = Field(gt=0, le=100_000_000)
    checksum_sha256: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)
    plan_code: str = "free"
    potentially_medical: bool = False


class PresignResponse(BaseModel):
    document_id: UUID
    state: str
    upload_url: str
    method: str
    expires_at: datetime
    headers: dict[str, str]
    purpose: str


class DocumentStatusResponse(BaseModel):
    id: UUID
    state: str
    display_name: str
    detected_type: str | None
    error_code: str | None
    created_at: datetime


class DocumentListItem(BaseModel):
    id: UUID
    state: str
    display_name: str
    detected_type: str | None
    updated_at: datetime
    latest_run_id: UUID | None = None
    latest_run_status: str | None = None


class BulkDeleteRequest(BaseModel):
    document_ids: list[UUID] = Field(min_length=1, max_length=100)


class BulkDeleteResponse(BaseModel):
    deleted: list[UUID]


class ExportResponse(BaseModel):
    user_id: str
    documents: list[dict]


class JobAckResponse(BaseModel):
    document_id: UUID
    state: str
    job_id: str
    idempotent_replay: bool = False


class ErrorBody(BaseModel):
    code: str
    detail: str


class ErasureProofResponse(BaseModel):
    document_id: str
    state: str
    tombstone_at: str | None
    blobs: list[dict]
    cache_cleared: bool
