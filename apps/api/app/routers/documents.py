from __future__ import annotations

from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as RawResponse

from app.routers.auth import current_user, get_auth_service
from app.schemas_documents import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    DocumentListItem,
    DocumentStatusResponse,
    ErasureProofResponse,
    ExportResponse,
    JobAckResponse,
    PresignResponse,
    UploadIntentRequest,
    UploadLimitsResponse,
)
from app.services.analysis.pipeline import AnalysisPipelineService
from app.services.auth_consent import AuthConsentError, AuthConsentService, UserRecord
from app.services.jobs.queue import enqueue_job
from app.services.upload.fsm import DocumentState
from app.services.upload.lifecycle import DocumentLifecycleService, DocumentStore, UploadError
from app.services.upload.safe_logging import safe_error_payload

router = APIRouter(prefix="/documents", tags=["documents"])


def get_doc_store(request: Request) -> DocumentStore:
    store = request.app.state.doc_store
    if not isinstance(store, DocumentStore):
        raise RuntimeError("Document store is not initialized")
    return store


def get_doc_service(request: Request) -> DocumentLifecycleService:
    service = request.app.state.doc_service
    if not isinstance(service, DocumentLifecycleService):
        raise RuntimeError("Document lifecycle service is not initialized")
    return service


def get_analysis_service(request: Request) -> AnalysisPipelineService:
    service = request.app.state.analysis_service
    if not isinstance(service, AnalysisPipelineService):
        raise RuntimeError("Analysis service is not initialized")
    return service


def _http(exc: UploadError) -> NoReturn:
    with safe_error_payload({"code": exc.code, "detail": exc.message}) as body:
        raise HTTPException(status_code=exc.http_status, detail=body)


def _require_user(user: UserRecord | None) -> UserRecord:
    if user is None:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    return user


def _require_admin(user: UserRecord | None = Depends(current_user)) -> UserRecord:
    principal = _require_user(user)
    # Never trust client headers or a job ID as maintenance authorization.
    # An account without an explicitly provisioned server-side admin role fails closed.
    if getattr(principal, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail={"code": "forbidden", "detail": "Admin only"})
    return principal


@router.get("", response_model=list[DocumentListItem])
async def list_documents(
    user: UserRecord | None = Depends(current_user),
    store: DocumentStore = Depends(get_doc_store),
    analysis: AnalysisPipelineService = Depends(get_analysis_service),
) -> list[DocumentListItem]:
    user = _require_user(user)
    items: list[DocumentListItem] = []
    for doc in store.documents.values():
        if doc.user_id != user.id or doc.tombstone_at is not None:
            continue
        run_ids = analysis.store.by_document.get(doc.id, [])
        latest_run = None
        if run_ids:
            latest_run = analysis.store.runs.get(run_ids[-1])
        items.append(
            DocumentListItem(
                id=doc.id,
                state=doc.state.value,
                display_name=doc.display_name,
                detected_type=doc.detected_type,
                updated_at=doc.updated_at,
                latest_run_id=latest_run.id if latest_run else None,
                latest_run_status=latest_run.status.value if latest_run else None,
            ),
        )
    items.sort(key=lambda d: d.updated_at, reverse=True)
    return items


@router.get("/upload-limits", response_model=UploadLimitsResponse)
async def upload_limits(request: Request) -> UploadLimitsResponse:
    from app.services.upload.validation import ALLOWED_EXTENSIONS, DEFAULT_MAX_BYTES

    settings = request.app.state.providers.settings
    return UploadLimitsResponse(
        max_bytes=DEFAULT_MAX_BYTES,
        max_pages=settings.max_analysis_pages,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
        formats_label="PDF, DOCX, JPEG, PNG",
    )


@router.post("/upload-intent", response_model=PresignResponse)
async def upload_intent(
    body: UploadIntentRequest,
    user: UserRecord | None = Depends(current_user),
    auth: AuthConsentService = Depends(get_auth_service),
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> PresignResponse:
    user = _require_user(user)
    try:
        feature = "document_medical" if body.potentially_medical else "document_ordinary"
        auth.assert_feature_allowed(user, feature)
    except AuthConsentError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "detail": exc.message},
        ) from exc

    try:
        doc, grant = service.create_upload_intent(
            user_id=user.id,
            tenant_id=user.tenant_id,
            plan_code=body.plan_code,
            display_filename=body.display_filename,
            content_type=body.content_type,
            size_bytes=body.size_bytes,
            checksum_sha256=body.checksum_sha256,
            idempotency_key=body.idempotency_key,
            potentially_medical=body.potentially_medical,
        )
    except UploadError as exc:
        _http(exc)
    return PresignResponse(
        document_id=doc.id,
        state=doc.state.value,
        upload_url=grant.url,
        method=grant.method,
        expires_at=grant.expires_at,
        headers=grant.headers,
        purpose=grant.purpose,
    )


@router.put("/upload/{document_id}")
async def upload_put(
    document_id: UUID,
    request: Request,
    token: str,
    purpose: str,
    exp: int,
    sig: str,
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> DocumentStatusResponse:
    data = await request.body()
    try:
        doc = await service.receive_bytes(
            document_id=document_id,
            token=token,
            purpose=purpose,
            exp=exp,
            sig=sig,
            data=data,
            declared_content_type=request.headers.get("content-type"),
        )
    except UploadError as exc:
        _http(exc)
    if doc.state == DocumentState.QUARANTINED:
        settings = request.app.state.providers.settings
        await enqueue_job(
            request.app.state.providers.redis,
            settings.queue_name,
            {"type": "scan", "document_id": str(document_id), "job_id": f"scan:{document_id}"},
        )
        request.app.state.flush_persistence()
        doc = service.store.documents[document_id]
    return DocumentStatusResponse(
        id=doc.id,
        state=doc.state.value,
        display_name=doc.display_name,
        detected_type=doc.detected_type,
        error_code=doc.error_code,
        created_at=doc.created_at,
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete(
    body: BulkDeleteRequest,
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
    analysis: AnalysisPipelineService = Depends(get_analysis_service),
) -> BulkDeleteResponse:
    user = _require_user(user)
    deleted = await service.bulk_delete(user_id=user.id, document_ids=body.document_ids)
    for document_id in deleted:
        analysis.purge_for_document(document_id, user.id)
    return BulkDeleteResponse(deleted=deleted)


@router.get("/export/me", response_model=ExportResponse)
async def export_me(
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> ExportResponse:
    user = _require_user(user)
    return ExportResponse(**service.export_user_data(user_id=user.id))


@router.post("/admin/purge-expired", dependencies=[Depends(_require_admin)])
async def purge_expired(service: DocumentLifecycleService = Depends(get_doc_service)) -> dict[str, int]:
    n = await service.purge_expired()
    return {"purged": n}


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document(
    document_id: UUID,
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> DocumentStatusResponse:
    user = _require_user(user)
    try:
        doc = service.get_owned(document_id, user.id)
    except UploadError as exc:
        _http(exc)
    return DocumentStatusResponse(
        id=doc.id,
        state=doc.state.value,
        display_name=doc.display_name,
        detected_type=doc.detected_type,
        error_code=doc.error_code,
        created_at=doc.created_at,
    )


@router.get("/{document_id}/download")
async def download(
    document_id: UUID,
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> RawResponse:
    user = _require_user(user)
    try:
        data = await service.download_derived(document_id=document_id, user_id=user.id)
        doc = service.get_owned(document_id, user.id)
    except UploadError as exc:
        _http(exc)
    return RawResponse(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.display_name}"'},
    )


@router.delete("/{document_id}", response_model=DocumentStatusResponse)
async def delete_one(
    document_id: UUID,
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
    analysis: AnalysisPipelineService = Depends(get_analysis_service),
) -> DocumentStatusResponse:
    user = _require_user(user)
    try:
        doc = await service.delete_document(document_id=document_id, user_id=user.id)
    except UploadError as exc:
        _http(exc)
    analysis.purge_for_document(document_id, user.id)
    return DocumentStatusResponse(
        id=doc.id,
        state=doc.state.value,
        display_name=doc.display_name,
        detected_type=doc.detected_type,
        error_code=doc.error_code,
        created_at=doc.created_at,
    )


@router.get("/{document_id}/erasure-proof", response_model=ErasureProofResponse)
async def erasure_proof(
    document_id: UUID,
    user: UserRecord | None = Depends(current_user),
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> ErasureProofResponse:
    user = _require_user(user)
    doc = service.store.documents.get(document_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"})
    return ErasureProofResponse(**service.verify_erasure(document_id))


@router.post(
    "/{document_id}/jobs/{job_type}",
    response_model=JobAckResponse,
    dependencies=[Depends(_require_admin)],
)
async def run_job(
    document_id: UUID,
    job_type: str,
    request: Request,
    service: DocumentLifecycleService = Depends(get_doc_service),
) -> JobAckResponse:
    job_id = request.headers.get("x-job-id") or f"{job_type}:{document_id}"
    doc_before = service.store.documents.get(document_id)
    already = bool(doc_before and job_id in doc_before.processed_jobs)
    try:
        if job_type == "scan":
            doc = await service.run_scan_job(document_id=document_id, job_id=job_id)
        elif job_type == "process":
            doc = await service.run_process_job(document_id=document_id, job_id=job_id)
        elif job_type == "purge":
            await service.purge_expired()
            doc = service._require(document_id)
        else:
            raise HTTPException(status_code=400, detail={"code": "unknown_job", "detail": "Unknown job"})
    except UploadError as exc:
        _http(exc)
    return JobAckResponse(
        document_id=doc.id,
        state=doc.state.value,
        job_id=job_id,
        idempotent_replay=already,
    )
