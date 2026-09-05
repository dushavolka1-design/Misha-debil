from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.persistence.bootstrap import mark_analysis_dirty
from app.routers.auth import current_user
from app.schemas_analysis import (
    AnalysisRunOut,
    CitationOut,
    FindingOut,
    PageOut,
    ProgressEventOut,
    RetryAnalysisRequest,
    StartAnalysisRequest,
    StartAnalysisResponse,
)
from app.schemas_rules import RuleHitOut
from app.services.analysis.pipeline import AnalysisError, AnalysisPipelineService, AnalysisStatus, LOCAL_STEP_LABELS
from app.services.jobs.queue import enqueue_job
from app.services.upload.fsm import DocumentState
from app.services.upload.lifecycle import DocumentLifecycleService, UploadError

router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_analysis(request: Request) -> AnalysisPipelineService:
    return request.app.state.analysis_service


def get_doc_service(request: Request) -> DocumentLifecycleService:
    return request.app.state.doc_service


def _require_user(user: object) -> None:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})


def _http(exc: AnalysisError | UploadError) -> None:
    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def serialize_run(service: AnalysisPipelineService, run) -> AnalysisRunOut:
    llm_available = bool(getattr(run, "llm_available", False))
    if not llm_available and run.llm_provider not in {"unavailable", "none", "fake_llm", ""}:
        llm_available = True
    local_steps = [
        LOCAL_STEP_LABELS.get(step, step) for step in (getattr(run, "local_steps", None) or [])
    ]
    return AnalysisRunOut(
        id=run.id,
        document_id=run.document_id,
        status=run.status.value,
        pipeline_version=run.pipeline_version,
        prompt_version=run.prompt_version,
        schema_version=run.schema_version,
        ocr_provider=run.ocr_provider,
        ocr_model_version=run.ocr_model_version,
        llm_provider=run.llm_provider,
        llm_model_version=run.llm_model_version,
        llm_available=llm_available,
        local_steps=local_steps,
        error_code=run.error_code,
        created_at=run.created_at,
        progress=[ProgressEventOut(**e) for e in service.progress_public(run)],
        pages=[
            PageOut(
                page_number=p.page_number,
                width=p.width,
                height=p.height,
                rotation=p.rotation,
                confidence=p.confidence,
                language=p.language,
                source=p.source,
                error_code=p.error_code,
                layout_region_types=[r["region_type"] for r in p.layout],
            )
            for p in run.pages
        ],
        findings=[
            FindingOut(
                id=f.id,
                kind=f.kind,
                entity_type=f.entity_type,
                raw_text=f.raw_text,
                normalized_value=f.normalized_value,
                confidence=f.confidence,
                uncertainty_state=f.uncertainty_state,
                citation=CitationOut(**f.citation),
            )
            for f in run.findings
        ],
        rejected_llm_count=len(run.rejected_llm),
        rule_hits=[RuleHitOut(**h) for h in run.rule_hits],
    )


@router.post("/runs", response_model=StartAnalysisResponse)
async def start_analysis(
    body: StartAnalysisRequest,
    request: Request,
    user=Depends(current_user),
    service: AnalysisPipelineService = Depends(get_analysis),
    doc_service: DocumentLifecycleService = Depends(get_doc_service),
) -> StartAnalysisResponse:
    _require_user(user)
    settings = request.app.state.providers.settings
    if body.fixture_id and not settings.demo_mode:
        raise HTTPException(
            status_code=400,
            detail={"code": "fixture_forbidden", "detail": "fixture_id доступен только в демонстрационном режиме"},
        )
    try:
        doc = doc_service.get_owned(body.document_id, user.id)
    except UploadError as exc:
        _http(exc)
        raise
    if doc.state != DocumentState.READY:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "document_not_ready",
                "detail": f"Документ должен быть в состоянии READY (сейчас: {doc.state.value})",
            },
        )

    run = service.start_run(
        document_id=body.document_id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        fixture_id=body.fixture_id if settings.demo_mode else None,
    )
    mark_analysis_dirty()
    payload: dict[str, str | None] = {
        "type": "analysis",
        "document_id": str(body.document_id),
        "run_id": str(run.id),
        "job_id": f"analysis:{run.id}",
    }
    if settings.demo_mode and body.fixture_id:
        payload["fixture_id"] = body.fixture_id
    await enqueue_job(request.app.state.providers.redis, settings.queue_name, payload)
    request.app.state.flush_persistence()

    return StartAnalysisResponse(
        run_id=run.id,
        status=run.status.value,
        pipeline_version=run.pipeline_version,
        prompt_version=run.prompt_version,
        schema_version=run.schema_version,
    )


@router.post("/runs/{run_id}/retry", response_model=StartAnalysisResponse)
async def retry_analysis(
    run_id: UUID,
    body: RetryAnalysisRequest,
    request: Request,
    user=Depends(current_user),
    service: AnalysisPipelineService = Depends(get_analysis),
) -> StartAnalysisResponse:
    _require_user(user)
    settings = request.app.state.providers.settings
    try:
        run = service.get_run(run_id, user.id)
    except AnalysisError as exc:
        _http(exc)
        raise
    if run.status not in {AnalysisStatus.FAILED, AnalysisStatus.READY}:
        raise HTTPException(
            status_code=409,
            detail={"code": "retry_not_allowed", "detail": "Повтор доступен только для завершённых или ошибочных запусков"},
        )
    run.status = AnalysisStatus.QUEUED
    run.error_code = None
    run.progress.clear()
    service._emit(run, "queued", 0)  # noqa: SLF001
    mark_analysis_dirty()
    await enqueue_job(
        request.app.state.providers.redis,
        settings.queue_name,
        {
            "type": "analysis",
            "document_id": str(run.document_id),
            "run_id": str(run.id),
            "job_id": f"analysis-retry:{run.id}:{body.stage}",
            "retry_stage": body.stage,
            "fixture_id": run.fixture_id,
        },
    )
    request.app.state.flush_persistence()
    return StartAnalysisResponse(
        run_id=run.id,
        status=run.status.value,
        pipeline_version=run.pipeline_version,
        prompt_version=run.prompt_version,
        schema_version=run.schema_version,
    )


@router.get("/runs/{run_id}", response_model=AnalysisRunOut)
async def get_run(
    run_id: UUID,
    user=Depends(current_user),
    service: AnalysisPipelineService = Depends(get_analysis),
) -> AnalysisRunOut:
    _require_user(user)
    try:
        run = service.get_run(run_id, user.id)
    except AnalysisError as exc:
        _http(exc)
        raise
    return serialize_run(service, run)


@router.get("/documents/{document_id}/runs", response_model=list[StartAnalysisResponse])
async def list_runs(
    document_id: UUID,
    user=Depends(current_user),
    service: AnalysisPipelineService = Depends(get_analysis),
) -> list[StartAnalysisResponse]:
    _require_user(user)
    runs = service.list_runs(document_id, user.id)
    return [
        StartAnalysisResponse(
            run_id=r.id,
            status=r.status.value,
            pipeline_version=r.pipeline_version,
            prompt_version=r.prompt_version,
            schema_version=r.schema_version,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}/progress", response_model=list[ProgressEventOut])
async def get_progress(
    run_id: UUID,
    user=Depends(current_user),
    service: AnalysisPipelineService = Depends(get_analysis),
) -> list[ProgressEventOut]:
    _require_user(user)
    try:
        run = service.get_run(run_id, user.id)
    except AnalysisError as exc:
        _http(exc)
        raise
    return [ProgressEventOut(**e) for e in service.progress_public(run)]
