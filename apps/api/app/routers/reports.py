from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.persistence.bootstrap import mark_blob_dirty
from app.routers.auth import current_user
from app.schemas_rules import (
    CompareDocumentsRequest,
    CompareRequest,
    CompareResponse,
    DiffItemOut,
    ExportReportRequest,
    ExportRunRequest,
    FeedbackRequest,
    FeedbackResponse,
    RegistryOut,
    RuleHitOut,
    RuleMetaOut,
    RunRulesRequest,
    RunRulesResponse,
)
from app.services.analysis.pipeline import AnalysisError, AnalysisStatus
from app.services.rules.compare import CompareDoc, CompareError, compare_documents
from app.services.rules.compare_loader import build_compare_doc_from_run
from app.services.rules.engine import registry_meta, run_rules
from app.services.rules.feedback import FeedbackKind, FeedbackStore
from app.services.rules.report import build_report, report_to_json, report_to_pdf_bytes
from app.services.rules.types import RuleHit, assert_safe_message
from app.services.upload.lifecycle import UploadError

router = APIRouter(prefix="/reports", tags=["reports"])


def get_feedback(request: Request) -> FeedbackStore:
    return request.app.state.feedback_store


def _require_user(user: object) -> None:
    if not user:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})


def _hit_out(h: RuleHit) -> RuleHitOut:
    return RuleHitOut(
        rule_id=h.rule_id,
        rule_version=h.rule_version,
        result_kind=h.result_kind.value,
        severity=h.severity.value,
        severity_rationale=h.severity_rationale,
        message=h.message,
        uncertainty=h.uncertainty.value,
        citations=h.citations,
        basis_fact_keys=h.basis_fact_keys,
        official_sources=h.official_sources,
    )


def _dict_hit(h: dict) -> RuleHitOut:
    return RuleHitOut(**h)


def _map_diffs(items):
    return [
        DiffItemOut(
            change=i.change,
            path=i.path,
            left_citation=i.left_citation,
            right_citation=i.right_citation,
            left_text=i.left_text,
            right_text=i.right_text,
        )
        for i in items
    ]


def _latest_ready_run(analysis_service, document_id: UUID, user_id: UUID):
    runs = analysis_service.list_runs(document_id, user_id)
    for run in reversed(runs):
        if run.status == AnalysisStatus.READY:
            return run
    return None


def _load_compare_doc(request: Request, document_id: UUID, user, payload: dict | None) -> CompareDoc:
    if payload:
        return CompareDoc(
            document_id=document_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
            title=str(payload.get("title", "")),
            sections=list(payload.get("sections") or []),
            parties=list(payload.get("parties") or []),
            clauses=list(payload.get("clauses") or []),
        )
    doc_service = request.app.state.doc_service
    analysis_service = request.app.state.analysis_service
    try:
        doc = doc_service.get_owned(document_id, user.id)
    except UploadError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    run = _latest_ready_run(analysis_service, document_id, user.id)
    if not run:
        raise HTTPException(
            status_code=409,
            detail={"code": "analysis_not_ready", "detail": "Нет готового анализа для сравнения"},
        )
    return build_compare_doc_from_run(
        document_id=document_id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        display_name=doc.display_name,
        run=run,
    )


@router.get("/rules", response_model=RegistryOut)
async def list_rules() -> RegistryOut:
    meta = registry_meta()
    return RegistryOut(
        registry_version=meta["registry_version"],
        rules=[RuleMetaOut(**r) for r in meta["rules"]],
    )


@router.post("/rules/run", response_model=RunRulesResponse)
async def rules_run(body: RunRulesRequest, user=Depends(current_user)) -> RunRulesResponse:
    _require_user(user)
    hits = run_rules(body.facts, document_type=body.document_type)
    model = [{**f, "origin": "model_inference"} for f in body.facts]
    return RunRulesResponse(
        document_id=body.document_id,
        rule_results=[_hit_out(h) for h in hits],
        model_findings=model,
    )


@router.post("/compare", response_model=CompareResponse)
async def compare(body: CompareRequest, request: Request, user=Depends(current_user)) -> CompareResponse:
    _require_user(user)
    left = _load_compare_doc(request, body.left_document_id, user, body.left)
    right = _load_compare_doc(request, body.right_document_id, user, body.right)
    try:
        result = compare_documents(left, right)
    except CompareError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    return CompareResponse(
        left_document_id=result.left_document_id,
        right_document_id=result.right_document_id,
        party_diffs=_map_diffs(result.party_diffs),
        section_diffs=_map_diffs(result.section_diffs),
        clause_diffs=_map_diffs(result.clause_diffs),
        refused=result.refused,
        refusal_reason=result.refusal_reason,
    )


@router.post("/compare/documents", response_model=CompareResponse)
async def compare_documents_route(
    body: CompareDocumentsRequest,
    request: Request,
    user=Depends(current_user),
) -> CompareResponse:
    _require_user(user)
    left_id = body.document_ids[0]
    right_id = body.document_ids[1]
    left = _load_compare_doc(request, left_id, user, None)
    right = _load_compare_doc(request, right_id, user, None)
    try:
        result = compare_documents(left, right)
    except CompareError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    return CompareResponse(
        left_document_id=result.left_document_id,
        right_document_id=result.right_document_id,
        party_diffs=_map_diffs(result.party_diffs),
        section_diffs=_map_diffs(result.section_diffs),
        clause_diffs=_map_diffs(result.clause_diffs),
        refused=result.refused,
        refusal_reason=result.refusal_reason,
    )


@router.post("/export")
async def export_report(body: ExportReportRequest, user=Depends(current_user)) -> Response:
    _require_user(user)
    hits = run_rules(body.facts, document_type=body.document_type)
    model = [{**f, "origin": "model_inference"} for f in body.facts]
    report = build_report(
        document_id=body.document_id,
        user_id=user.id,
        analysis_run_id=body.analysis_run_id,
        model_findings=model,
        rule_hits=hits,
        unanalyzed_pages=body.unanalyzed_pages,
    )
    assert_safe_message(report.disclaimer)
    if body.format == "pdf":
        data = report_to_pdf_bytes(report)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
        )
    data = report_to_json(report)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.json"'},
    )


@router.post("/export/run")
async def export_run(body: ExportRunRequest, request: Request, user=Depends(current_user)) -> Response:
    _require_user(user)
    analysis = request.app.state.analysis_service
    try:
        run = analysis.get_run(body.analysis_run_id, user.id)
    except AnalysisError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message}) from exc
    if run.status != AnalysisStatus.READY:
        raise HTTPException(
            status_code=409,
            detail={"code": "not_ready", "detail": "Экспорт доступен только для завершённого анализа"},
        )
    facts = [
        {
            "entity_type": f.entity_type,
            "raw_text": f.raw_text,
            "normalized_value": f.normalized_value,
            "citation": f.citation,
            "kind": f.kind,
            "origin": "model_inference" if f.kind == "inference" else "local_extract",
        }
        for f in run.findings
        if f.entity_type != "analysis.capability"
    ]
    from app.services.rules.types import ResultKind, Severity, Uncertainty

    parsed_hits: list[RuleHit] = []
    for h in run.rule_hits:
        parsed_hits.append(
            RuleHit(
                rule_id=h["rule_id"],
                rule_version=h["rule_version"],
                result_kind=ResultKind(h["result_kind"]),
                severity=Severity(h["severity"]),
                severity_rationale=h["severity_rationale"],
                message=h["message"],
                uncertainty=Uncertainty(h["uncertainty"]),
                citations=h.get("citations", []),
                basis_fact_keys=h.get("basis_fact_keys", []),
                official_sources=h.get("official_sources", []),
            ),
        )
    unanalyzed = [p.page_number for p in run.pages if p.error_code]
    report = build_report(
        document_id=run.document_id,
        user_id=user.id,
        analysis_run_id=run.id,
        model_findings=facts,
        rule_hits=parsed_hits,
        unanalyzed_pages=unanalyzed,
    )
    assert_safe_message(report.disclaimer)
    if body.format == "pdf":
        data = report_to_pdf_bytes(report)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report-{run.id}.pdf"'},
        )
    data = report_to_json(report)
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report-{run.id}.json"'},
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    body: FeedbackRequest,
    user=Depends(current_user),
    store: FeedbackStore = Depends(get_feedback),
) -> FeedbackResponse:
    _require_user(user)
    ev = store.add(
        user_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        kind=FeedbackKind(body.kind),
        comment=body.comment,
    )
    mark_blob_dirty("feedback")
    return FeedbackResponse(
        id=ev.id,
        message="Отзыв сохранён. Результаты анализа автоматически не меняются.",
        mutates_results=False,
    )
