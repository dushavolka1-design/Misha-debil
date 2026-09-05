from __future__ import annotations

"""Pixel-perfect form fill API — separate prefix to avoid /forms/{uuid} clashes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.routers.auth import current_user
from app.schemas_forms import (
    CoordMapApproveRequest,
    CoordMapSubmitRequest,
    FillDraftSaveRequest,
    FillGenerateRequest,
    FillPreDownloadRequest,
    FillPreviewRequest,
)
from app.services.forms.catalog import FormCatalogService, FormError
from app.services.forms.fill.engine import FillError, engine_info
from app.services.forms.fill.generation_gates import inferred_form_kind, is_test_synthetic_slug
from app.services.forms.fill.service import FormFillService

router = APIRouter(prefix="/forms/fill", tags=["form-fill"])


def get_fill(request: Request) -> FormFillService:
    return request.app.state.form_fill


def get_catalog(request: Request) -> FormCatalogService:
    return request.app.state.form_catalog


def _http(exc: FillError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


@router.get("/engine")
async def fill_engine_info() -> dict:
    return engine_info()


@router.get("/by-catalog/{catalog_form_id}")
async def fill_by_catalog(
    catalog_form_id: UUID,
    fill: FormFillService = Depends(get_fill),
    catalog: FormCatalogService = Depends(get_catalog),
) -> dict:
    try:
        form = catalog.get(catalog_form_id)
    except FormError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    card = catalog.card(form)
    return fill.fill_package(catalog_form_id=catalog_form_id, catalog_card=card)


@router.get("/drafts")
async def get_fill_draft(
    catalog_form_id: UUID,
    fill: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    draft = fill.get_draft(user_id=user.id, catalog_form_id=catalog_form_id)
    if not draft:
        return {"draft": None}
    return {"draft": fill.draft_card(draft) | {"answers": draft.answers}}


@router.put("/drafts")
async def save_fill_draft(
    body: FillDraftSaveRequest,
    fill: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        draft = fill.save_draft(user_id=user.id, catalog_form_id=body.catalog_form_id, answers=body.answers)
    except FillError as exc:
        _http(exc)
        raise
    return {"draft": fill.draft_card(draft) | {"answers": draft.answers}}


@router.get("/generated")
async def list_generated_forms(
    fill: FormFillService = Depends(get_fill),
    catalog: FormCatalogService = Depends(get_catalog),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    drafts = [
        fill.draft_card(
            d,
            catalog_title=(
                catalog.forms[d.catalog_form_id].title
                if d.catalog_form_id in catalog.forms and hasattr(catalog.forms[d.catalog_form_id], "title")
                else None
            ),
        )
        | {"answers": d.answers}
        for d in fill.list_drafts(user_id=user.id)
    ]
    generated = []
    for g in fill.list_generated_for_user(user_id=user.id):
        title = None
        rec = catalog.forms.get(g.catalog_form_id) if g.catalog_form_id else None
        if rec is not None and hasattr(rec, "title"):
            title = rec.title
        generated.append(fill.generated_card(g, catalog_title=title))
    return {"drafts": drafts, "generated": generated}


@router.post("/generated/{generated_id}/copy")
async def copy_generated_form(
    generated_id: UUID,
    fill: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        rec = fill.copy_generated(generated_id, user_id=user.id)
    except FillError as exc:
        _http(exc)
        raise
    return {
        "generated_id": str(rec.id),
        "preview": rec.preview,
    }


@router.post("/pre-download")
async def pre_download_checklist(
    body: FillPreDownloadRequest,
    fill: FormFillService = Depends(get_fill),
) -> dict:
    try:
        return fill.pre_download_checklist(body.form_version_id, body.answers)
    except FillError as exc:
        _http(exc)
        raise


@router.get("/versions")
async def list_fill_versions(service: FormFillService = Depends(get_fill)) -> list[dict]:
    return [service.version_card(v) for v in service.versions.values() if not is_test_synthetic_slug(v.slug)]


@router.get("/versions/{version_id}")
async def get_fill_version(version_id: UUID, service: FormFillService = Depends(get_fill)) -> dict:
    ver = service.versions.get(version_id)
    if not ver:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"})
    return service.version_card(ver)


@router.get("/versions/{version_id}/underlay")
async def get_underlay_pdf(version_id: UUID, service: FormFillService = Depends(get_fill)) -> Response:
    ver = service.versions.get(version_id)
    if not ver or is_test_synthetic_slug(ver.slug):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"})
    kind = inferred_form_kind(ver.slug)
    if kind == "government_form" and (ver.source_snapshot_id is None or ver.review_status != "published"):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail={"code": "not_available", "detail": "Оригинал государственной формы ещё не подтверждён."},
        )
    filename = {
        "medical_memo": "pamyatka-vizit.pdf",
        "service_worksheet": "chernovik-svedeniy.pdf",
    }.get(kind, "form.pdf")
    return Response(
        content=ver.original_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/coord-maps/submit")
async def submit_coord_map(body: CoordMapSubmitRequest, service: FormFillService = Depends(get_fill)) -> dict:
    try:
        draft = service.submit_coord_map_for_review(
            form_version_id=body.form_version_id,
            map_json=body.map_json,
            author_id=body.author_id,
        )
    except FillError as exc:
        _http(exc)
        raise
    return {"draft_id": str(draft.id), "status": draft.status}


@router.post("/coord-maps/approve")
async def approve_coord_map(body: CoordMapApproveRequest, service: FormFillService = Depends(get_fill)) -> dict:
    try:
        ver = service.approve_coord_map(body.draft_id, reviewer_id=body.reviewer_id)
    except FillError as exc:
        _http(exc)
        raise
    return service.version_card(ver)


@router.post("/preview")
async def preview_fill(body: FillPreviewRequest, service: FormFillService = Depends(get_fill)) -> dict:
    try:
        result = service.preview(body.form_version_id, body.answers)
    except FillError as exc:
        _http(exc)
        raise
    return result.to_dict()


@router.post("/generate")
async def generate_fill(
    body: FillGenerateRequest,
    service: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        rec = service.generate(form_version_id=body.form_version_id, user_id=user.id, answers=body.answers)
    except FillError as exc:
        _http(exc)
        raise
    return {
        "generated_id": str(rec.id),
        "template_hash": rec.template_hash,
        "coord_map_hash": rec.coord_map_hash,
        "input_hash": rec.input_hash,
        "output_hash": rec.output_hash,
        "engine_version": rec.engine_version,
        "preview": rec.preview,
    }


@router.get("/generated/{generated_id}/pdf")
async def download_generated(
    generated_id: UUID,
    service: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> Response:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        rec = service.get_generated(generated_id, user_id=user.id)
    except FillError as exc:
        _http(exc)
        raise
    from urllib.parse import quote

    from app.services.forms.fill.generation_gates import download_stem

    ver = service.versions.get(rec.form_version_id)
    stem = download_stem(ver.slug) if ver else "document"
    utf_name = f"{stem}.pdf"
    ascii_name = f"{stem}-{generated_id}.pdf"
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(utf_name)}"
    return Response(
        content=rec.output_pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": disposition},
    )


@router.delete("/generated/{generated_id}")
async def delete_generated(
    generated_id: UUID,
    service: FormFillService = Depends(get_fill),
    user=Depends(current_user),
) -> dict:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        service.delete_generated(generated_id, user_id=user.id)
    except FillError as exc:
        _http(exc)
        raise
    return {"ok": True}
