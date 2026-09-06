from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from dar.providers.ports import KMSProvider, MalwareScanner, ObjectStorage

from app.services.upload.encryption import Envelope, decrypt_envelope, encrypt_envelope
from app.services.upload.filename import opaque_object_key, sanitize_display_filename
from app.services.upload.fsm import DocumentState, InvalidTransition, can_user_download, transition
from app.services.upload.retention import (
    DEFAULT_RETENTION,
    MEDICAL_RETENTION,
    RetentionPolicy,
    expires_at,
    retention_for_kind,
)
from app.services.upload.validation import (
    DEFAULT_MAX_BYTES,
    EXT_BY_TYPE,
    DetectedType,
    harden_by_type,
    validate_upload,
)

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {"max_uploads_per_day": 20, "max_bytes": 10 * 1024 * 1024},
    "pro": {"max_uploads_per_day": 200, "max_bytes": 50 * 1024 * 1024},
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class UploadError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class StoredBlobMeta:
    bucket: str
    key: str
    kind: str
    content_type: str
    size_bytes: int
    content_hash: str
    dek_id: str | None
    wrapped_dek: bytes | None
    erased_at: datetime | None = None
    expires_at: datetime | None = None


@dataclass
class DocumentRecord:
    id: UUID
    user_id: UUID
    tenant_id: UUID
    state: DocumentState
    display_name: str
    declared_content_type: str
    expected_checksum: str | None
    detected_type: str | None = None
    plan_code: str = "free"
    idempotency_key: str | None = None
    upload_token: str | None = None
    upload_token_purpose: str = "put"
    upload_token_expires: datetime | None = None
    upload_token_used: bool = False
    error_code: str | None = None
    malware_signature: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    tombstone_at: datetime | None = None
    legal_hold: bool = False
    blobs: dict[str, StoredBlobMeta] = field(default_factory=dict)
    extracted_text_ref: str | None = None  # opaque key only, never log text
    processed_jobs: set[str] = field(default_factory=set)
    retention_expires_at: datetime | None = None
    is_medical: bool = False
    access_role: str = "standard"  # standard|medical_restricted


@dataclass
class PresignGrant:
    url: str
    method: str
    expires_at: datetime
    headers: dict[str, str]
    document_id: UUID
    purpose: str


class DocumentStore:
    def __init__(self) -> None:
        self.documents: dict[UUID, DocumentRecord] = {}
        self.by_idempotency: dict[tuple[UUID, str], UUID] = {}
        self.upload_tokens: dict[str, UUID] = {}
        self.destroyed_deks: set[str] = set()
        self.cache: dict[str, bytes] = {}
        self.audit: list[dict[str, Any]] = []
        self.uploads_today: dict[tuple[UUID, str], int] = {}

    def audit_event(self, **kwargs: Any) -> None:
        # Never accept filename/text fields into audit kwargs from callers unchecked
        safe = {k: v for k, v in kwargs.items() if k not in {"filename", "extracted_text", "quote", "text"}}
        safe["at"] = utcnow().isoformat()
        self.audit.append(safe)


class DocumentLifecycleService:
    """In-memory lifecycle for local/test; mirrors durable schema semantics."""

    def __init__(
        self,
        store: DocumentStore,
        *,
        storage: ObjectStorage,
        malware: MalwareScanner,
        kms: KMSProvider,
        bucket_quarantine: str,
        bucket_originals: str,
        bucket_derived: str,
        bucket_reports: str,
        retention: RetentionPolicy = DEFAULT_RETENTION,
        presign_secret: str = "local_presign_secret",
        sandbox_cpu_seconds: float = 5.0,
        sandbox_memory_hint_mb: int = 256,
        now_fn=utcnow,
    ) -> None:
        self.store = store
        self.storage = storage
        self.malware = malware
        self.kms = kms
        self.bucket_quarantine = bucket_quarantine
        self.bucket_originals = bucket_originals
        self.bucket_derived = bucket_derived
        self.bucket_reports = bucket_reports
        self.retention = retention
        self.medical_retention = MEDICAL_RETENTION
        self.presign_secret = presign_secret.encode()
        self.sandbox_cpu_seconds = sandbox_cpu_seconds
        self.sandbox_memory_hint_mb = sandbox_memory_hint_mb
        self.now = now_fn
        # Holds plaintext DEKs until destroy (local/fake KMS)
        self._deks: dict[str, bytes] = {}

    def _set_state(self, doc: DocumentRecord, target: DocumentState) -> None:
        try:
            doc.state = transition(doc.state, target)
        except InvalidTransition as exc:
            raise UploadError("invalid_transition", str(exc), http_status=409) from exc
        doc.updated_at = self.now()

    def _day_key(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def create_upload_intent(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        plan_code: str,
        display_filename: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str | None = None,
        idempotency_key: str | None = None,
        potentially_medical: bool = False,
    ) -> tuple[DocumentRecord, PresignGrant]:
        limits = PLAN_LIMITS.get(plan_code, PLAN_LIMITS["free"])
        if size_bytes > limits["max_bytes"]:
            raise UploadError("plan_size_exceeded", "File exceeds plan size limit", http_status=403)
        day = self._day_key()
        count = self.store.uploads_today.get((user_id, day), 0)
        if count >= limits["max_uploads_per_day"]:
            raise UploadError("plan_quota_exceeded", "Daily upload quota exceeded", http_status=403)

        if idempotency_key:
            existing_id = self.store.by_idempotency.get((user_id, idempotency_key))
            if existing_id and existing_id in self.store.documents:
                doc = self.store.documents[existing_id]
                grant = self._presign_for(doc, purpose="put")
                return doc, grant

        doc_id = uuid4()
        safe_name = sanitize_display_filename(display_filename)
        token = secrets.token_urlsafe(32)
        expires = self.now() + timedelta(minutes=10)
        policy = self.medical_retention if potentially_medical else self.retention
        doc = DocumentRecord(
            id=doc_id,
            user_id=user_id,
            tenant_id=tenant_id,
            state=DocumentState.CREATED,
            display_name=safe_name,
            declared_content_type=content_type,
            expected_checksum=checksum_sha256,
            plan_code=plan_code,
            idempotency_key=idempotency_key,
            upload_token=token,
            upload_token_purpose="put",
            upload_token_expires=expires,
            retention_expires_at=expires_at(self.now(), retention_for_kind(policy, "original")),
            is_medical=potentially_medical,
            access_role="medical_restricted" if potentially_medical else "standard",
        )
        self._set_state(doc, DocumentState.UPLOADING)
        self.store.documents[doc_id] = doc
        self.store.upload_tokens[token] = doc_id
        self.store.uploads_today[(user_id, day)] = count + 1
        if idempotency_key:
            self.store.by_idempotency[(user_id, idempotency_key)] = doc_id
        self.store.audit_event(
            action="upload_intent",
            document_id=str(doc_id),
            user_id=str(user_id),
            medical=potentially_medical,
        )
        return doc, self._presign_for(doc, purpose="put")

    def assert_document_access(self, doc: DocumentRecord, *, user_id: UUID, user_role: str = "user") -> None:
        if doc.user_id == user_id:
            return
        if doc.access_role == "medical_restricted":
            if user_role not in {"medical_reviewer", "admin"}:
                raise UploadError("medical_access_denied", "Medical document access restricted", http_status=403)
            return
        raise UploadError("access_denied", "Document access denied", http_status=403)

    def _presign_for(self, doc: DocumentRecord, *, purpose: str) -> PresignGrant:
        assert doc.upload_token
        exp = int((doc.upload_token_expires or self.now()).timestamp())
        sig = hmac.new(
            self.presign_secret,
            f"{purpose}:{doc.id}:{doc.upload_token}:{exp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        url = f"/documents/upload/{doc.id}?token={doc.upload_token}&purpose={purpose}&exp={exp}&sig={sig}"
        return PresignGrant(
            url=url,
            method="PUT" if purpose == "put" else "GET",
            expires_at=doc.upload_token_expires or self.now(),
            headers={"Content-Type": doc.declared_content_type},
            document_id=doc.id,
            purpose=purpose,
        )

    def verify_presign(self, *, document_id: UUID, token: str, purpose: str, exp: int, sig: str) -> DocumentRecord:
        if int(self.now().timestamp()) > exp:
            raise UploadError("presign_expired", "Upload URL expired", http_status=403)
        expected = hmac.new(
            self.presign_secret,
            f"{purpose}:{document_id}:{token}:{exp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise UploadError("presign_invalid", "Invalid upload URL", http_status=403)
        doc = self.store.documents.get(document_id)
        if not doc or doc.upload_token != token:
            raise UploadError("presign_invalid", "Invalid upload URL", http_status=403)
        if purpose != doc.upload_token_purpose:
            raise UploadError("presign_purpose", "URL purpose mismatch", http_status=403)
        if purpose == "put" and doc.upload_token_used:
            raise UploadError("presign_replay", "Single-purpose URL already used", http_status=409)
        return doc

    async def receive_bytes(
        self,
        *,
        document_id: UUID,
        token: str,
        purpose: str,
        exp: int,
        sig: str,
        data: bytes,
        declared_content_type: str | None = None,
    ) -> DocumentRecord:
        doc = self.verify_presign(document_id=document_id, token=token, purpose=purpose, exp=exp, sig=sig)
        if purpose != "put":
            raise UploadError("presign_purpose", "PUT required", http_status=405)
        if doc.user_id and doc.state not in {DocumentState.UPLOADING, DocumentState.CREATED}:
            raise UploadError("invalid_state", "Not accepting upload", http_status=409)

        limits = PLAN_LIMITS.get(doc.plan_code, PLAN_LIMITS["free"])
        result = validate_upload(
            data=data,
            declared_filename=doc.display_name,
            declared_content_type=declared_content_type or doc.declared_content_type,
            expected_checksum=doc.expected_checksum,
            max_bytes=limits.get("max_bytes", DEFAULT_MAX_BYTES),
        )
        if not result.ok or result.detected is None:
            self._set_state(doc, DocumentState.REJECTED)
            doc.error_code = result.reason or "validation_failed"
            doc.upload_token_used = True
            self.store.audit_event(action="reject", document_id=str(doc.id), code=doc.error_code)
            return doc

        # Envelope encrypt into quarantine — app must not serve this bucket
        dek = await self.kms.create_dek(purpose=f"doc:{doc.id}")
        dek_id = f"dek-{doc.id}"
        wrapped = await self.kms.wrap_dek(dek=dek)
        self._deks[dek_id] = dek
        env = encrypt_envelope(plaintext=data, dek=dek, dek_id=dek_id, wrapped_dek=wrapped)
        key = opaque_object_key(
            tenant_id=str(doc.tenant_id),
            document_id=str(doc.id),
            kind="quarantine",
            ext=EXT_BY_TYPE[result.detected],
        )
        await self.storage.put_bytes(
            bucket=self.bucket_quarantine,
            key=key,
            data=env.ciphertext,
            content_type="application/octet-stream",
        )
        doc.blobs["quarantine"] = StoredBlobMeta(
            bucket=self.bucket_quarantine,
            key=key,
            kind="quarantine",
            content_type=result.content_type or "application/octet-stream",
            size_bytes=len(data),
            content_hash=result.sha256,
            dek_id=dek_id,
            wrapped_dek=wrapped,
            expires_at=doc.retention_expires_at,
        )
        doc.detected_type = result.detected.value
        doc.upload_token_used = True
        self._set_state(doc, DocumentState.QUARANTINED)
        self.store.audit_event(action="quarantined", document_id=str(doc.id), size=len(data))
        return doc

    async def run_scan_job(self, *, document_id: UUID, job_id: str) -> DocumentRecord:
        doc = self._require(document_id)
        if job_id in doc.processed_jobs:
            return doc  # idempotent
        if doc.state == DocumentState.QUARANTINED:
            self._set_state(doc, DocumentState.SCANNING)
        elif doc.state != DocumentState.SCANNING:
            if doc.state in {DocumentState.CLEAN, DocumentState.READY, DocumentState.INFECTED, DocumentState.REJECTED}:
                doc.processed_jobs.add(job_id)
                return doc
            raise UploadError("invalid_state", "Cannot scan", http_status=409)

        data = await self._read_quarantine_plaintext(doc)
        # Pass opaque name to scanner — never original path
        scan = await self.malware.scan(data=data, filename=f"{doc.id}.bin")
        if not scan.clean:
            self._set_state(doc, DocumentState.INFECTED)
            doc.malware_signature = scan.signature
            doc.error_code = "infected"
            doc.processed_jobs.add(job_id)
            self.store.audit_event(action="infected", document_id=str(doc.id), signature=scan.signature)
            return doc

        ok, reason = harden_by_type(data, DetectedType(doc.detected_type or "pdf"))
        if not ok:
            self._set_state(doc, DocumentState.REJECTED)
            doc.error_code = reason
            doc.processed_jobs.add(job_id)
            self.store.audit_event(action="harden_reject", document_id=str(doc.id), code=reason)
            return doc

        self._set_state(doc, DocumentState.CLEAN)
        doc.processed_jobs.add(job_id)
        self.store.audit_event(action="clean", document_id=str(doc.id))
        return doc

    async def run_process_job(self, *, document_id: UUID, job_id: str) -> DocumentRecord:
        doc = self._require(document_id)
        if job_id in doc.processed_jobs:
            return doc
        if doc.state == DocumentState.CLEAN:
            self._set_state(doc, DocumentState.PROCESSING)
        elif doc.state != DocumentState.PROCESSING:
            if doc.state == DocumentState.READY:
                doc.processed_jobs.add(job_id)
                return doc
            raise UploadError("invalid_state", "Not clean; refuse processing", http_status=409)

        started = time.perf_counter()
        data = await self._read_quarantine_plaintext(doc)
        # Sandbox limits: time budget; no network (enforced by not calling external clients here)
        if time.perf_counter() - started > self.sandbox_cpu_seconds:
            self._set_state(doc, DocumentState.FAILED)
            doc.error_code = "sandbox_timeout"
            doc.processed_jobs.add(job_id)
            return doc
        _ = self.sandbox_memory_hint_mb

        # Move encrypted original to originals bucket; write tiny derived stub (not user-download of quarantine)
        q = doc.blobs["quarantine"]
        orig_key = opaque_object_key(
            tenant_id=str(doc.tenant_id),
            document_id=str(doc.id),
            kind="original",
            ext=doc.detected_type or "bin",
        )
        cipher = await self.storage.get_bytes(bucket=q.bucket, key=q.key)
        await self.storage.put_bytes(
            bucket=self.bucket_originals,
            key=orig_key,
            data=cipher,
            content_type="application/octet-stream",
        )
        doc.blobs["original"] = StoredBlobMeta(
            bucket=self.bucket_originals,
            key=orig_key,
            kind="original",
            content_type=q.content_type,
            size_bytes=q.size_bytes,
            content_hash=q.content_hash,
            dek_id=q.dek_id,
            wrapped_dek=q.wrapped_dek,
            expires_at=expires_at(self.now(), retention_for_kind(self.retention, "original")),
        )

        # Extracted text stored as derived object — content never logged
        text_bytes = f"normalized:{doc.detected_type}:{q.content_hash[:12]}".encode()
        text_key = opaque_object_key(
            tenant_id=str(doc.tenant_id),
            document_id=str(doc.id),
            kind="extracted_text",
            ext="txt",
        )
        await self.storage.put_bytes(
            bucket=self.bucket_derived,
            key=text_key,
            data=text_bytes,
            content_type="text/plain",
        )
        doc.blobs["extracted_text"] = StoredBlobMeta(
            bucket=self.bucket_derived,
            key=text_key,
            kind="extracted_text",
            content_type="text/plain",
            size_bytes=len(text_bytes),
            content_hash=hashlib.sha256(text_bytes).hexdigest(),
            dek_id=None,
            wrapped_dek=None,
            expires_at=expires_at(self.now(), retention_for_kind(self.retention, "extracted_text")),
        )
        doc.extracted_text_ref = text_key
        self.store.cache.pop(f"doc:{doc.id}:text", None)

        self._set_state(doc, DocumentState.READY)
        doc.processed_jobs.add(job_id)
        self.store.audit_event(action="ready", document_id=str(doc.id))
        return doc

    async def _read_quarantine_plaintext(self, doc: DocumentRecord) -> bytes:
        blob = doc.blobs.get("quarantine")
        if not blob or not blob.dek_id:
            raise UploadError("no_quarantine", "No quarantine object", http_status=404)
        if blob.dek_id in self.store.destroyed_deks:
            raise UploadError("erased", "DEK destroyed", http_status=410)
        cipher = await self.storage.get_bytes(bucket=blob.bucket, key=blob.key)
        dek = self._deks.get(blob.dek_id)
        if dek is None:
            raise UploadError("dek_missing", "DEK unavailable", http_status=410)
        env = Envelope(dek_id=blob.dek_id, wrapped_dek=blob.wrapped_dek or b"", ciphertext=cipher)
        return decrypt_envelope(envelope=env, dek=dek)

    async def read_plaintext_for_analysis(self, document_id: UUID) -> bytes:
        doc = self._require(document_id)
        if doc.state not in {DocumentState.CLEAN, DocumentState.PROCESSING, DocumentState.READY}:
            raise UploadError("invalid_state", "Document not ready for analysis", http_status=409)
        return await self._read_quarantine_plaintext(doc)

    def _require(self, document_id: UUID) -> DocumentRecord:
        doc = self.store.documents.get(document_id)
        if not doc:
            raise UploadError("not_found", "Document not found", http_status=404)
        return doc

    def get_owned(self, document_id: UUID, user_id: UUID) -> DocumentRecord:
        doc = self._require(document_id)
        if doc.user_id != user_id:
            raise UploadError("forbidden", "Not found", http_status=404)  # no IDOR leak
        if doc.state == DocumentState.DELETED:
            raise UploadError("gone", "Deleted", http_status=410)
        return doc

    async def download_derived(self, *, document_id: UUID, user_id: UUID, kind: str = "extracted_text") -> bytes:
        doc = self.get_owned(document_id, user_id)
        if not can_user_download(doc.state):
            raise UploadError("not_ready", "File not available until READY/clean pipeline complete", http_status=403)
        if kind == "quarantine":
            raise UploadError("quarantine_forbidden", "Quarantine is not downloadable", http_status=403)
        blob = doc.blobs.get(kind)
        if not blob or blob.erased_at:
            raise UploadError("not_found", "Artifact missing", http_status=404)
        return await self.storage.get_bytes(bucket=blob.bucket, key=blob.key)

    async def delete_document(self, *, document_id: UUID, user_id: UUID) -> DocumentRecord:
        doc = self.get_owned(document_id, user_id)
        if doc.legal_hold:
            raise UploadError("legal_hold", "partial_hold", http_status=423)
        if doc.state != DocumentState.DELETING:
            self._set_state(doc, DocumentState.DELETING)
        await self._erase(doc)
        self._set_state(doc, DocumentState.DELETED)
        doc.tombstone_at = self.now()
        self.store.audit_event(action="deleted", document_id=str(doc.id), user_id=str(user_id))
        return doc

    async def bulk_delete(self, *, user_id: UUID, document_ids: list[UUID]) -> list[UUID]:
        done: list[UUID] = []
        for did in document_ids:
            try:
                await self.delete_document(document_id=did, user_id=user_id)
                done.append(did)
            except UploadError:
                continue
        return done

    async def _erase(self, doc: DocumentRecord) -> None:
        for blob in list(doc.blobs.values()):
            if blob.dek_id:
                await self.kms.destroy_dek(dek_id=blob.dek_id)
                self.store.destroyed_deks.add(blob.dek_id)
                self._deks.pop(blob.dek_id, None)
            await self.storage.delete_object(bucket=blob.bucket, key=blob.key)
            blob.erased_at = self.now()
        self.store.cache.pop(f"doc:{doc.id}:text", None)
        doc.extracted_text_ref = None

    def export_user_data(self, *, user_id: UUID) -> dict[str, Any]:
        """Export without secrets, risk scores, or other users' data."""
        items = []
        for doc in self.store.documents.values():
            if doc.user_id != user_id:
                continue
            if doc.state == DocumentState.DELETED:
                continue
            items.append(
                {
                    "id": str(doc.id),
                    "state": doc.state.value,
                    "display_name": doc.display_name,
                    "detected_type": doc.detected_type,
                    "created_at": doc.created_at.isoformat(),
                    "blobs": [
                        {
                            "kind": b.kind,
                            "size_bytes": b.size_bytes,
                            "content_hash": b.content_hash,
                            "erased": b.erased_at is not None,
                        }
                        for b in doc.blobs.values()
                        if b.kind != "quarantine"
                    ],
                },
            )
        return {"user_id": str(user_id), "documents": items}

    async def purge_expired(self) -> int:
        n = 0
        now = self.now()
        for doc in list(self.store.documents.values()):
            if doc.state in {DocumentState.DELETED, DocumentState.DELETING}:
                continue
            if doc.legal_hold:
                continue
            exp = doc.retention_expires_at
            if exp and exp <= now:
                if doc.state != DocumentState.EXPIRED:
                    try:
                        self._set_state(doc, DocumentState.EXPIRED)
                    except UploadError:
                        pass
                if doc.state != DocumentState.DELETING:
                    try:
                        self._set_state(doc, DocumentState.DELETING)
                    except UploadError:
                        doc.state = DocumentState.DELETING
                await self._erase(doc)
                doc.state = DocumentState.DELETED
                doc.tombstone_at = now
                n += 1
                self.store.audit_event(action="purged", document_id=str(doc.id))
        return n

    def verify_erasure(self, document_id: UUID) -> dict[str, Any]:
        doc = self._require(document_id)
        return {
            "document_id": str(doc.id),
            "state": doc.state.value,
            "tombstone_at": doc.tombstone_at.isoformat() if doc.tombstone_at else None,
            "blobs": [
                {
                    "kind": b.kind,
                    "erased_at": b.erased_at.isoformat() if b.erased_at else None,
                    "dek_destroyed": b.dek_id in self.store.destroyed_deks if b.dek_id else None,
                }
                for b in doc.blobs.values()
            ],
            "cache_cleared": f"doc:{doc.id}:text" not in self.store.cache,
        }
