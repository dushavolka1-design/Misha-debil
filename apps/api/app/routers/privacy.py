from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app.routers.auth import current_user, get_auth_service
from app.schemas_auth import (
    ConsentActionRequest,
    MessageResponse,
    PrivacyDashboardResponse,
    UploadGateRequest,
    UploadGateResponse,
    WithdrawRequest,
)
from app.services.auth_consent import SPECIAL_MEDICAL, AuthConsentError, AuthConsentService

router = APIRouter(prefix="/privacy", tags=["privacy"])


def _http(exc: AuthConsentError) -> HTTPException:
    return HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


@router.get("/dashboard", response_model=PrivacyDashboardResponse)
async def dashboard(
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> PrivacyDashboardResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    data = service.privacy_dashboard(user)
    return PrivacyDashboardResponse(**data)


@router.post("/consents/accept", response_model=MessageResponse)
async def accept_consent(
    body: ConsentActionRequest,
    request: Request,
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MessageResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    if not body.consent_version or not body.content_hash:
        raise HTTPException(status_code=400, detail={"code": "invalid", "detail": "version and hash required"})
    ip = request.client.host if request.client else None
    try:
        service.accept(
            user,
            consent_id=body.consent_id,
            consent_version=body.consent_version,
            content_hash=body.content_hash,
            locale=body.locale,
            ip=ip,
            user_agent=request.headers.get("user-agent"),
            request_id=request.headers.get("x-request-id") or str(uuid4()),
        )
    except AuthConsentError as exc:
        raise _http(exc) from exc
    return MessageResponse(message="accepted")


@router.post("/consents/withdraw", response_model=MessageResponse)
async def withdraw_consent(
    body: WithdrawRequest,
    request: Request,
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MessageResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    ip = request.client.host if request.client else None
    try:
        service.withdraw(
            user,
            consent_id=body.consent_id,
            locale=body.locale,
            ip=ip,
            user_agent=request.headers.get("user-agent"),
            request_id=request.headers.get("x-request-id") or str(uuid4()),
        )
    except AuthConsentError as exc:
        raise _http(exc) from exc
    extra = ""
    if body.consent_id == SPECIAL_MEDICAL:
        extra = " " + service.medical_withdraw_consequences()["summary"]
    return MessageResponse(message="withdrawn." + extra)


@router.get("/consents/medical/consequences")
async def medical_consequences(service: AuthConsentService = Depends(get_auth_service)) -> dict:
    return service.medical_withdraw_consequences()


@router.post("/export-request", response_model=MessageResponse)
async def export_request(
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MessageResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    # Allowed even if offer re-consent pending
    service.request_export(user)
    return MessageResponse(message="Export requested")


@router.post("/delete-request", response_model=MessageResponse)
async def delete_request(
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> MessageResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    service.request_deletion(user)
    return MessageResponse(message="Deletion requested")


@router.post("/upload-gate", response_model=UploadGateResponse)
async def upload_gate(
    body: UploadGateRequest,
    service: AuthConsentService = Depends(get_auth_service),
    user=Depends(current_user),
) -> UploadGateResponse:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    feature = "document_medical" if body.potentially_medical else "document_ordinary"
    try:
        service.assert_feature_allowed(user, feature)
    except AuthConsentError as exc:
        if exc.code == "consent_required":
            missing = [p.strip() for p in exc.message.split(":", 1)[-1].split(",")]
            return UploadGateResponse(allowed=False, code="consent_required", missing=missing)
        raise _http(exc) from exc
    return UploadGateResponse(allowed=True, code="ok", missing=[])
