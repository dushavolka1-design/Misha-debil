from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class FindingKind(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"


@dataclass(frozen=True, slots=True)
class BBox:
    """Coordinates in page space (origin top-left, units = page points/pixels)."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True, slots=True)
class OcrSpan:
    text: str
    bbox: BBox
    confidence: float
    language: str = "und"


@dataclass(frozen=True, slots=True)
class OcrBlock:
    block_type: str  # word|line|block
    text: str
    bbox: BBox
    confidence: float
    language: str
    children: tuple[OcrSpan, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrPageResult:
    page_number: int
    text: str
    confidence: float
    width: float
    height: float
    rotation: int
    language: str
    words: tuple[OcrSpan, ...] = ()
    lines: tuple[OcrSpan, ...] = ()
    blocks: tuple[OcrBlock, ...] = ()
    source: str = "ocr"  # ocr|native_pdf|hybrid
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class OcrDocumentResult:
    pages: list[OcrPageResult]
    provider: str
    model_version: str


@dataclass(frozen=True, slots=True)
class LlmAnalysisResult:
    findings: list[dict[str, Any]]
    provider: str
    model_version: str
    raw_refusal: bool = False
    schema_valid: bool = True
    rejection_reason: str | None = None


@dataclass(frozen=True, slots=True)
class StoredObject:
    bucket: str
    key: str
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class MalwareScanResult:
    clean: bool
    signature: str | None = None
    provider: str = "unknown"


@dataclass(frozen=True, slots=True)
class PaymentSession:
    provider_ref: str
    status: str
    checkout_url: str | None = None
    amount_minor: int | None = None
    currency: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    receipts: bool
    refunds: bool
    recurring: bool
    sandbox_only: bool
    notes: str = ""


@dataclass(frozen=True, slots=True)
class WebhookVerification:
    ok: bool
    event_id: str | None = None
    event_type: str | None = None
    occurred_at: str | None = None
    reason: str | None = None
    sanitized_payload: dict[str, Any] = field(default_factory=dict)


class OCRProvider(ABC):
    name: str
    model_version: str = "unknown"

    @abstractmethod
    async def extract_text(self, *, object_ref: StoredObject, content_type: str) -> OcrDocumentResult:
        raise NotImplementedError

    async def extract_layout(
        self,
        *,
        object_ref: StoredObject,
        content_type: str,
        page_bytes: bytes | None = None,
        fixture_id: str | None = None,
    ) -> OcrDocumentResult:
        """Prefer layout-aware extraction; default falls back to extract_text."""
        _ = (page_bytes, fixture_id)
        return await self.extract_text(object_ref=object_ref, content_type=content_type)


class LLMProvider(ABC):
    name: str
    model_version: str = "unknown"

    @abstractmethod
    async def analyze_document(
        self,
        *,
        text: str,
        document_id: UUID,
        purpose: str,
    ) -> LlmAnalysisResult:
        raise NotImplementedError

    async def extract_facts(
        self,
        *,
        fragment: str,
        document_id: UUID,
        json_schema: dict[str, Any],
        system_instructions: str,
        prompt_version: str,
    ) -> LlmAnalysisResult:
        """Fragment-only extraction with schema; default adapters may override."""
        _ = (json_schema, system_instructions, prompt_version)
        return await self.analyze_document(text=fragment, document_id=document_id, purpose="extract_facts")


class ObjectStorage(ABC):
    name: str

    @abstractmethod
    async def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    async def get_bytes(self, *, bucket: str, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def delete_object(self, *, bucket: str, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def head_bucket(self, *, bucket: str) -> bool:
        raise NotImplementedError


class MalwareScanner(ABC):
    name: str

    @abstractmethod
    async def scan(self, *, data: bytes, filename: str) -> MalwareScanResult:
        raise NotImplementedError


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    async def create_checkout(self, *, user_id: UUID, plan_code: str) -> PaymentSession:
        raise NotImplementedError

    async def create_payment_intent(
        self,
        *,
        user_id: UUID,
        plan_code: str,
        amount_minor: int,
        currency: str,
        idempotency_key: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentSession:
        """Server-priced intent. Default delegates to create_checkout (amount ignored by legacy)."""
        _ = (amount_minor, currency, idempotency_key, description, metadata)
        return await self.create_checkout(user_id=user_id, plan_code=plan_code)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            receipts=False,
            refunds=False,
            recurring=False,
            sandbox_only=True,
            notes="default capabilities",
        )

    def verify_webhook(
        self,
        *,
        headers: dict[str, str],
        raw_body: bytes,
        now_ts: float | None = None,
    ) -> WebhookVerification:
        _ = (headers, raw_body, now_ts)
        return WebhookVerification(ok=False, reason="webhook_not_supported")

    async def cancel_recurring(self, *, provider_subscription_ref: str) -> dict[str, Any]:
        return {"ok": True, "provider_ref": provider_subscription_ref, "status": "cancel_requested"}

    async def request_refund(self, *, provider_payment_ref: str, amount_minor: int | None = None) -> dict[str, Any]:
        _ = amount_minor
        return {
            "ok": False,
            "reason": "refunds_require_provider_capability_and_review",
            "provider_ref": provider_payment_ref,
        }


class EmailProvider(ABC):
    name: str

    @abstractmethod
    async def send(self, *, to: str, subject: str, body_text: str) -> None:
        raise NotImplementedError


class KMSProvider(ABC):
    name: str

    @abstractmethod
    async def create_dek(self, *, purpose: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def destroy_dek(self, *, dek_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def wrap_dek(self, *, dek: bytes) -> bytes:
        raise NotImplementedError
