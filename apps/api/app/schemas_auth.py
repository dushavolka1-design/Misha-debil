from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class LegalActiveItem(BaseModel):
    id: UUID
    consent_id: str
    consent_version: str
    locale: str
    content_hash: str
    effective_at: datetime
    body_path: str


class AcceptInput(BaseModel):
    consent_id: str
    consent_version: str
    content_hash: str = Field(min_length=64, max_length=64)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)
    locale: str = "ru-RU"
    accepts: list[AcceptInput]
    avatar_data_url: str | None = Field(default=None, max_length=600_000)


class RegisterResponse(BaseModel):
    message: str
    # Only present in local/test to ease e2e without mailer
    verification_token_dev: str | None = None


class LoginRequest(BaseModel):
    password: str
    username: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=320)

    @model_validator(mode="after")
    def _identifier(self) -> LoginRequest:
        ident = (self.username or self.email or "").strip()
        if len(ident) < 2:
            raise ValueError("Укажите имя пользователя")
        self.username = ident
        return self


class MessageResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str


class MeResponse(BaseModel):
    id: UUID
    email: str
    status: str
    email_verified: bool
    display_name: str = ""
    has_avatar: bool = False


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    avatar_data_url: str | None = Field(default=None, max_length=600_000)
    clear_avatar: bool = False


class ConsentActionRequest(BaseModel):
    consent_id: str
    consent_version: str | None = None
    content_hash: str | None = None
    locale: str = "ru-RU"


class WithdrawRequest(BaseModel):
    consent_id: str
    locale: str = "ru-RU"


class PrivacyDashboardResponse(BaseModel):
    user_id: str
    email: str
    display_name: str = ""
    has_avatar: bool = False
    email_verified: bool
    consents: list[dict]
    deletion_requested_at: datetime | None
    export_requested_at: datetime | None


class ProofResponse(BaseModel):
    event_id: UUID
    content_hash: str
    canonical_text: str


class UploadGateRequest(BaseModel):
    potentially_medical: bool = False
    filename: str


class UploadGateResponse(BaseModel):
    allowed: bool
    code: Literal["ok", "consent_required"] = "ok"
    missing: list[str] = []


class ErrorBody(BaseModel):
    code: str
    detail: str
