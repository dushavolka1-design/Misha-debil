from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.routers.auth import current_user
from app.schemas_entry import DraftResponse, EvaluateResponse, QuestionnaireIn, VisaRegimeOut
from app.services.entry.checklist_pdf import render_checklist_pdf
from app.services.entry.engine import EntryError, EntryWizardService, Questionnaire, StepResult
from app.services.entry.form_recommendations import recommend_catalog_forms
from app.services.forms.catalog import FormCatalogService

router = APIRouter(prefix="/entry", tags=["entry-wizard"])


def get_entry(request: Request) -> EntryWizardService:
    return request.app.state.entry_wizard


def _http(exc: EntryError) -> None:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def _q(body: QuestionnaireIn) -> Questionnaire:
    return Questionnaire(
        citizenship=body.citizenship,
        second_citizenship=body.second_citizenship,
        second_citizenship_code=body.second_citizenship_code,
        age_band=body.age_band,
        visa_regime_id=body.visa_regime_id,
        purpose=body.purpose,
        planned_stay_days=body.planned_stay_days,
        planned_entry_date=body.planned_entry_date,
        eaeu_member=body.eaeu_member,
        invitation=body.invitation,
        host_type=body.host_type,
        region_code=body.region_code,
        special_statuses=list(body.special_statuses),
        plans_extension_or_change=body.plans_extension_or_change,
        timezone=body.timezone,
        draft_consent=body.draft_consent,
    )


def get_catalog(request: Request) -> FormCatalogService:
    return request.app.state.form_catalog


def _stages(stages: dict[str, list[StepResult]]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for k, steps in stages.items():
        out[k] = []
        for s in steps:
            d = asdict(s)
            out[k].append(d)
    return out


def _evaluate_response(snap, catalog: FormCatalogService, q: Questionnaire) -> EvaluateResponse:
    reviewed_at = None
    for steps in snap.stages.values():
        for step in steps:
            if step.as_of:
                reviewed_at = step.as_of
                break
        if reviewed_at:
            break
    if not reviewed_at and getattr(snap, "created_at", None):
        reviewed_at = snap.created_at.date().isoformat()
    return EvaluateResponse(
        snapshot_id=snap.id,
        pack_version=snap.pack_version,
        disclaimer=snap.disclaimer,
        unknown_case=snap.unknown_case,
        activated_rule_ids=snap.activated_rule_ids,
        freshness_blocked_rules=snap.freshness_blocked_rules,
        stages=_stages(snap.stages),
        questionnaire=snap.questionnaire,
        recommended_forms=recommend_catalog_forms(catalog, q),
        reviewed_at=reviewed_at,
    )


def _checklist_payload(snap) -> dict[str, list[str] | str]:
    steps: list[str] = []
    documents: list[str] = []
    sources: list[str] = []
    reviewed_at = ""
    for stage_steps in snap.stages.values():
        for step in stage_steps:
            if step.title:
                steps.append(str(step.title))
            if step.prepare:
                documents.append(str(step.prepare))
            for src in step.official_sources or []:
                label = src.get("official_url") or src.get("title")
                if label:
                    sources.append(str(label))
            if step.as_of:
                reviewed_at = str(step.as_of)
    if not reviewed_at and getattr(snap, "created_at", None):
        reviewed_at = snap.created_at.date().isoformat()
    unique_sources = list(dict.fromkeys(sources))
    return {
        "title": "Чеклист въезда и пребывания",
        "steps": steps,
        "documents": documents,
        "official_source": "; ".join(unique_sources) if unique_sources else "Источник уточняется",
        "reviewed_at": reviewed_at or "уточняется",
    }


def _questionnaire_from_snap(snap) -> Questionnaire:
    qdict = snap.questionnaire
    from datetime import date

    return Questionnaire(
        citizenship=qdict["citizenship"],
        second_citizenship=bool(qdict.get("second_citizenship")),
        second_citizenship_code=qdict.get("second_citizenship_code"),
        age_band=qdict.get("age_band") or "adult",
        visa_regime_id=qdict.get("visa_regime_id"),
        purpose=qdict.get("purpose") or "tourism",
        planned_stay_days=qdict.get("planned_stay_days"),
        planned_entry_date=date.fromisoformat(qdict["planned_entry_date"]) if qdict.get("planned_entry_date") else None,
        eaeu_member=bool(qdict.get("eaeu_member")),
        invitation=bool(qdict.get("invitation")),
        host_type=qdict.get("host_type"),
        region_code=qdict.get("region_code"),
        special_statuses=list(qdict.get("special_statuses") or []),
        plans_extension_or_change=bool(qdict.get("plans_extension_or_change")),
        timezone=qdict.get("timezone") or "Europe/Moscow",
        draft_consent=True,
    )


@router.get("/visa-regimes", response_model=list[VisaRegimeOut])
async def visa_regimes(service: EntryWizardService = Depends(get_entry)) -> list[VisaRegimeOut]:
    return [VisaRegimeOut(**x) for x in service.visa_regime_catalog()]


@router.post("/drafts", response_model=DraftResponse)
async def save_draft(
    body: QuestionnaireIn,
    service: EntryWizardService = Depends(get_entry),
    user=Depends(current_user),
) -> DraftResponse:
    try:
        rec = service.save_draft(_q(body), user_id=getattr(user, "id", None))
    except EntryError as exc:
        _http(exc)
        raise
    return DraftResponse(draft_id=rec.id, message="Draft saved with consent")


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    body: QuestionnaireIn,
    service: EntryWizardService = Depends(get_entry),
    catalog: FormCatalogService = Depends(get_catalog),
) -> EvaluateResponse:
    q = _q(body)
    try:
        snap = service.evaluate(q)
    except EntryError as exc:
        _http(exc)
        raise
    return _evaluate_response(snap, catalog, q)


@router.post("/snapshots/{snapshot_id}/refresh", response_model=EvaluateResponse)
async def refresh(
    snapshot_id: UUID,
    service: EntryWizardService = Depends(get_entry),
    catalog: FormCatalogService = Depends(get_catalog),
) -> EvaluateResponse:
    try:
        snap = service.refresh(snapshot_id)
    except EntryError as exc:
        _http(exc)
        raise
    return _evaluate_response(snap, catalog, _questionnaire_from_snap(snap))


@router.get("/snapshots/{snapshot_id}", response_model=EvaluateResponse)
async def get_snapshot(
    snapshot_id: UUID,
    service: EntryWizardService = Depends(get_entry),
    catalog: FormCatalogService = Depends(get_catalog),
) -> EvaluateResponse:
    snap = service.snapshots.get(snapshot_id)
    if not snap:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"})
    return _evaluate_response(snap, catalog, _questionnaire_from_snap(snap))


@router.post("/snapshots/{snapshot_id}/checklist.pdf")
async def export_checklist_pdf(
    snapshot_id: UUID,
    service: EntryWizardService = Depends(get_entry),
) -> Response:
    snap = service.snapshots.get(snapshot_id)
    if not snap:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Чеклист не найден"})
    payload = _checklist_payload(snap)
    pdf = render_checklist_pdf(
        title=str(payload["title"]),
        steps=list(payload["steps"]),
        documents=list(payload["documents"]),
        official_source=str(payload["official_source"]),
        reviewed_at=str(payload["reviewed_at"]),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="checklist-informational.pdf"'},
    )
