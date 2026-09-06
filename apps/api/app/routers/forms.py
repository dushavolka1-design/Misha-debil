from __future__ import annotations

import base64
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.persistence.form_catalog_codec import CATALOG_FATAL_MESSAGE
from app.persistence.form_catalog_repo import list_quarantine
from app.routers.auth import current_user, get_auth_service
from app.schemas_forms import (
    AbuseReportRequest,
    AbuseReportResponse,
    FormCardOut,
    FormRegisterRequest,
    MedicalOrgRegisterRequest,
    MedicalPdfRequest,
    MedicalProcedureRegisterRequest,
)
from app.services.auth_consent import AuthConsentError, AuthConsentService, UserRecord
from app.services.forms.catalog import FormCatalogService, FormError
from app.services.forms.medical import MedicalError, MedicalSectionService
from app.services.forms.pdf_memo import MedicalPdfError, describe_policy

router = APIRouter(prefix="/forms", tags=["forms-catalog"])


def get_forms(request: Request) -> FormCatalogService:
    service = request.app.state.form_catalog
    if not isinstance(service, FormCatalogService):
        raise RuntimeError("Form catalog service is not initialized")
    return service


def get_medical(request: Request) -> MedicalSectionService:
    service = request.app.state.medical_section
    if not isinstance(service, MedicalSectionService):
        raise RuntimeError("Medical section service is not initialized")
    return service


def _http_form(exc: FormError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def _http_med(exc: MedicalError | MedicalPdfError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def _catalog_fatal(request: Request) -> None:
    err = getattr(request.app.state, "catalog_persistence_error", None)
    if not err:
        return
    from fastapi import HTTPException

    raise HTTPException(
        status_code=503,
        detail={
            "code": err.get("code") or "catalog_load_failed",
            "detail": err.get("detail") or CATALOG_FATAL_MESSAGE,
            "correlation_id": err.get("correlation_id") or "",
        },
    )


@router.get("", response_model=list[FormCardOut])
async def list_forms(
    request: Request,
    organ: str | None = None,
    purpose: str | None = None,
    status: str | None = None,
    region: str | None = None,
    category: str | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=128),
    as_of: date | None = None,
    service: FormCatalogService = Depends(get_forms),
) -> list[FormCardOut]:
    _catalog_fatal(request)
    forms = service.list_forms(
        organ=organ,
        purpose=purpose,
        status=status,
        region=region,
        category=category,
        search=search,
        as_of=as_of,
    )
    return [FormCardOut(**service.card(f)) for f in forms]


@router.get("/categories")
async def list_categories() -> list[dict[str, str]]:
    from app.services.forms.catalog_seed import CATEGORIES

    return [{"id": k, "label": v} for k, v in CATEGORIES.items()]


@router.get("/mvp-verification")
async def mvp_verification(service: FormCatalogService = Depends(get_forms)) -> dict[str, Any]:
    return {"log": service.verification_log, "forms": [service.card(f) for f in service.iter_records()]}


@router.get("/diagnostics")
async def catalog_diagnostics(
    request: Request,
    service: FormCatalogService = Depends(get_forms),
) -> dict[str, Any]:
    err = getattr(request.app.state, "catalog_persistence_error", None)
    return {
        "ok": not err and service.typed_catalog_ok(),
        "persistence_error": err,
        "isolated": list(service.quarantine) + list_quarantine(),
        "loaded_count": len(service.iter_records()),
    }


@router.get("/medical/policy")
async def medical_policy() -> dict[str, Any]:
    return describe_policy()


@router.get("/medical/procedures")
async def medical_procedures(service: MedicalSectionService = Depends(get_medical)) -> list[dict[str, Any]]:
    return service.list_procedures()


@router.get("/medical/orgs")
async def medical_orgs(
    region_code: str | None = None,
    as_of: date | None = Query(default=None),
    service: MedicalSectionService = Depends(get_medical),
) -> list[dict[str, Any]]:
    return service.list_orgs(region_code=region_code, as_of=as_of)


@router.post("/medical/procedures")
async def register_procedure(
    body: MedicalProcedureRegisterRequest,
    service: MedicalSectionService = Depends(get_medical),
    user: UserRecord | None = Depends(current_user),
) -> dict[str, str]:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        p = service.register_procedure(
            slug=body.slug,
            title=body.title,
            explanation=body.explanation,
            applicable_to=body.applicable_to,
            deadline_text=body.deadline_text,
            source_snapshot_id=body.source_snapshot_id,
            checklist=body.checklist,
            questionnaire_fields=body.questionnaire_fields,
        )
    except MedicalError as exc:
        _http_med(exc)
        raise
    return {"id": str(p.id), "slug": p.slug, "status": p.status}


@router.post("/medical/orgs")
async def register_org(
    body: MedicalOrgRegisterRequest,
    service: MedicalSectionService = Depends(get_medical),
    user: UserRecord | None = Depends(current_user),
) -> dict[str, str]:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        o = service.register_org(
            name=body.name,
            region_code=body.region_code,
            source_snapshot_id=body.source_snapshot_id,
            valid_from=body.valid_from,
            valid_to=body.valid_to,
        )
    except MedicalError as exc:
        _http_med(exc)
        raise
    return {"id": str(o.id), "name": o.name, "region_code": o.region_code}


@router.post("/medical/pdf")
async def medical_pdf(
    body: MedicalPdfRequest,
    service: MedicalSectionService = Depends(get_medical),
    auth: AuthConsentService = Depends(get_auth_service),
    user: UserRecord | None = Depends(current_user),
) -> Response:
    """Generate only questionnaire/checklist/memo. Forbidden kinds → 403 at backend."""
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        auth.assert_feature_allowed(user, "document_medical")
    except AuthConsentError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    try:
        pdf = service.generate_artifact_pdf(
            kind=body.kind,
            title=body.title,
            body_lines=body.body_lines,
            answers=body.answers,
        )
    except (MedicalError, MedicalPdfError) as exc:
        _http_med(exc)
        raise
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="medical-memo-preliminary.pdf"'},
    )


@router.post("/register", response_model=FormCardOut)
async def register_form(
    body: FormRegisterRequest,
    service: FormCatalogService = Depends(get_forms),
    user: UserRecord | None = Depends(current_user),
) -> FormCardOut:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        raw = base64.b64decode(body.raw_base64)
        rec = service.register_form(
            slug=body.slug,
            title=body.title,
            organ=body.organ,
            purpose=body.purpose,
            region=body.region,
            authority=body.authority,
            source_snapshot_id=body.source_snapshot_id,
            raw_original=raw,
            content_sha256=body.content_sha256.lower(),
            act_number=body.act_number,
            act_date=body.act_date,
            act_title=body.act_title,
            valid_from=body.valid_from,
            valid_to=body.valid_to,
            reviewed_at=body.reviewed_at,
            reviewer=body.reviewer,
            warning=body.warning or "Не является официальной подачей в госорган.",
        )
    except FormError as exc:
        _http_form(exc)
        raise
    except Exception as exc:  # noqa: BLE001
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail={"code": "bad_raw", "detail": str(exc)}) from exc
    return FormCardOut(**service.card(rec))


@router.post("/abuse-reports", response_model=AbuseReportResponse)
async def abuse_report(
    body: AbuseReportRequest,
    service: FormCatalogService = Depends(get_forms),
    user: UserRecord | None = Depends(current_user),
) -> AbuseReportResponse:
    try:
        rep = service.report_abuse(
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
            comment=body.comment,
            reporter_user_id=getattr(user, "id", None),
        )
    except FormError as exc:
        _http_form(exc)
        raise
    return AbuseReportResponse(id=rep.id, message="Abuse/outdated report accepted")


@router.get("/{form_id}", response_model=FormCardOut)
async def get_form(form_id: UUID, request: Request, service: FormCatalogService = Depends(get_forms)) -> FormCardOut:
    _catalog_fatal(request)
    try:
        f = service.get(form_id)
    except FormError as exc:
        _http_form(exc)
        raise
    return FormCardOut(**service.card(f))
