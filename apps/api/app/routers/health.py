from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import ProviderBundle, check_database, check_object_storage, check_queue
from app.schemas import (
    HealthResponse,
    InstanceResponse,
    LiveResponse,
    PublicConfigResponse,
    ReadinessChecks,
    ReadinessResponse,
)
from app.settings import Settings, get_settings

router = APIRouter(tags=["health"])


def get_bundle() -> ProviderBundle:
    # Overridden in main lifespan
    raise RuntimeError("Provider bundle not initialized")


@router.get("/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    return LiveResponse()


@router.get("/instance", response_model=InstanceResponse)
async def instance(settings: Settings = Depends(get_settings)) -> InstanceResponse:
    import os

    return InstanceResponse(
        product="docly",
        instance_token=settings.instance_token or "",
        pid=os.getpid(),
        profile=settings.docly_profile or settings.app_env,
    )


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(service=settings.app_name, env=settings.app_env)


@router.get("/config/public", response_model=PublicConfigResponse)
async def public_config(settings: Settings = Depends(get_settings)) -> PublicConfigResponse:
    return PublicConfigResponse(
        demo_mode=settings.demo_mode,
        max_analysis_pages=settings.max_analysis_pages,
        ocr_provider=settings.ocr_provider,
        llm_provider=settings.llm_provider,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def ready(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    bundle: ProviderBundle = Depends(get_bundle),
) -> ReadinessResponse:
    db_ok = False
    queue_ok = False
    storage_ok = False
    catalog_ok = False
    font_ok = False
    generation_ok = False
    try:
        db_ok = await check_database(session)
    except Exception:
        db_ok = False
    try:
        queue_ok = await check_queue(bundle)
    except Exception:
        queue_ok = False
    try:
        storage_ok = await check_object_storage(bundle)
    except Exception:
        storage_ok = False
    try:
        if getattr(request.app.state, "catalog_persistence_error", None):
            catalog_ok = False
        else:
            catalog = request.app.state.form_catalog
            catalog_ok = bool(catalog.typed_catalog_ok())
    except Exception:
        catalog_ok = False
    try:
        from app.services.forms.fill.fonts import bundled_font_status

        font_ok = bundled_font_status().ok
    except Exception:
        font_ok = False
    try:
        from app.services.forms.capabilities import generation_capabilities

        caps = generation_capabilities(
            catalog=request.app.state.form_catalog,
            fill=request.app.state.form_fill,
        )
        generation_ok = bool(caps.get("generation_ready"))
        font_ok = bool(caps.get("font_ready"))
    except Exception:
        generation_ok = False

    checks = ReadinessChecks(
        database=db_ok,
        queue=queue_ok,
        object_storage=storage_ok,
        catalog=catalog_ok,
        font=font_ok,
        generation=generation_ok,
    )
    ok = db_ok and queue_ok and storage_ok and catalog_ok and font_ok
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="ready" if ok else "not_ready", checks=checks)


@router.get("/capabilities")
async def capabilities(request: Request) -> dict:
    from app.services.forms.capabilities import generation_capabilities

    catalog = getattr(request.app.state, "form_catalog", None)
    fill = getattr(request.app.state, "form_fill", None)
    if catalog is None or fill is None:
        return {
            "catalog_ready": False,
            "fill_engine_ready": False,
            "font_ready": False,
            "official_templates_count": 0,
            "generation_ready": False,
            "reasons": ["Сервис ещё запускается."],
        }
    return generation_capabilities(catalog=catalog, fill=fill)
