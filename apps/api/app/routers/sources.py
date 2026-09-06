from __future__ import annotations

from typing import Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.routers.auth import current_user
from app.schemas_sources import (
    AuditOut,
    CitationRequest,
    CitationResponse,
    DiffOut,
    ReviewDecision,
    ReviewTaskOut,
    SeedResponse,
    SnapshotOut,
    SourceOut,
)
from app.services.auth_consent import UserRecord
from app.services.sources.registry import SnapshotRecord, SourceError, SourceRegistry
from app.services.sources.url_policy import load_allowlist

router = APIRouter(prefix="/sources", tags=["sources"])


def get_registry(request: Request) -> SourceRegistry:
    registry = request.app.state.source_registry
    if not isinstance(registry, SourceRegistry):
        raise RuntimeError("Source registry is not initialized")
    return registry


def _http(exc: SourceError) -> NoReturn:
    from fastapi import HTTPException

    raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "detail": exc.message})


def _snap_out(s: SnapshotRecord) -> SnapshotOut:
    return SnapshotOut(
        id=s.id,
        source_id=s.source_id,
        state=s.state.value,
        content_hash=s.content_hash,
        final_url=s.final_url,
        fetched_at=s.fetched_at.isoformat(),
        parser_version=s.parser_version,
        link_status=s.link_status,
        reviewer_id=s.reviewer_id,
        review_comment=s.review_comment,
        valid_from=s.valid_from,
        valid_to=s.valid_to,
        act_title=s.act_title,
        act_number=s.act_number,
        act_date=s.act_date,
    )


@router.post("/seed", response_model=SeedResponse)
async def seed(registry: SourceRegistry = Depends(get_registry)) -> SeedResponse:
    created = registry.seed_from_allowlist()
    return SeedResponse(created=len(created), allowlist_version=registry.cfg.version)


@router.get("", response_model=list[SourceOut])
async def list_sources(registry: SourceRegistry = Depends(get_registry)) -> list[SourceOut]:
    return [
        SourceOut(
            id=s.id,
            slug=s.slug,
            title=s.title,
            organ=s.organ,
            official_url=s.official_url,
            host=s.host,
            state=s.state.value,
            criticality=s.criticality,
        )
        for s in registry.sources.values()
    ]


@router.post("/{source_id}/fetch", response_model=SnapshotOut)
async def fetch_source(
    source_id: UUID,
    registry: SourceRegistry = Depends(get_registry),
    user: UserRecord | None = Depends(current_user),
) -> SnapshotOut:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        snap = registry.fetch_and_parse(source_id, actor=getattr(user, "email", "editor"))
    except SourceError as exc:
        _http(exc)
    return _snap_out(snap)


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut)
async def get_snapshot(snapshot_id: UUID, registry: SourceRegistry = Depends(get_registry)) -> SnapshotOut:
    snap = registry.snapshots.get(snapshot_id)
    if not snap:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"})
    return _snap_out(snap)


@router.get("/snapshots/{snapshot_id}/production-visible")
async def production_visible(snapshot_id: UUID, registry: SourceRegistry = Depends(get_registry)) -> dict[str, bool]:
    return {"usable_as_basis": registry.production_basis_visible(snapshot_id)}


@router.get("/diff/{old_id}/{new_id}", response_model=DiffOut)
async def diff(old_id: UUID, new_id: UUID, registry: SourceRegistry = Depends(get_registry)) -> DiffOut:
    try:
        return DiffOut(diff=registry.diff_snapshots(old_id, new_id))
    except KeyError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found", "detail": "Not found"}) from exc


@router.post("/snapshots/{snapshot_id}/approve", response_model=SnapshotOut)
async def approve(
    snapshot_id: UUID,
    body: ReviewDecision,
    registry: SourceRegistry = Depends(get_registry),
    user: UserRecord | None = Depends(current_user),
) -> SnapshotOut:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        snap = registry.approve(
            snapshot_id,
            actor=getattr(user, "email", "reviewer"),
            comment=body.comment,
            valid_from=body.valid_from,
            valid_to=body.valid_to,
            act_title=body.act_title,
            act_number=body.act_number,
            act_date=body.act_date,
        )
    except SourceError as exc:
        _http(exc)
    return _snap_out(snap)


@router.post("/snapshots/{snapshot_id}/reject", response_model=SnapshotOut)
async def reject(
    snapshot_id: UUID,
    body: ReviewDecision,
    registry: SourceRegistry = Depends(get_registry),
    user: UserRecord | None = Depends(current_user),
) -> SnapshotOut:
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail={"code": "unauthorized", "detail": "Not authenticated"})
    try:
        snap = registry.reject(snapshot_id, actor=getattr(user, "email", "reviewer"), comment=body.comment)
    except SourceError as exc:
        _http(exc)
    return _snap_out(snap)


@router.post("/citations", response_model=CitationResponse)
async def cite(body: CitationRequest, registry: SourceRegistry = Depends(get_registry)) -> CitationResponse:
    try:
        payload = registry.citation(body.snapshot_id, quote=body.quote, on_date=body.on_date)
    except SourceError as exc:
        _http(exc)
    return CitationResponse(payload=payload)


@router.get("/review-tasks", response_model=list[ReviewTaskOut])
async def review_tasks(registry: SourceRegistry = Depends(get_registry)) -> list[ReviewTaskOut]:
    return [
        ReviewTaskOut(
            id=t.id,
            source_id=t.source_id,
            snapshot_id=t.snapshot_id,
            reason=t.reason,
            status=t.status,
            created_at=t.created_at.isoformat(),
        )
        for t in registry.review_tasks
    ]


@router.get("/audit", response_model=list[AuditOut])
async def audit_log(registry: SourceRegistry = Depends(get_registry)) -> list[AuditOut]:
    return [
        AuditOut(
            id=a.id,
            at=a.at.isoformat(),
            actor=a.actor,
            action=a.action,
            source_id=a.source_id,
            snapshot_id=a.snapshot_id,
            detail=a.detail,
        )
        for a in registry.audit
    ]


@router.get("/allowlist")
async def allowlist_meta() -> dict[str, Any]:
    cfg = load_allowlist()
    return {
        "version": cfg.version,
        "hosts": [{"host": h.host, "organ": h.organ, "criticality": h.criticality} for h in cfg.hosts],
        "default": "deny",
    }


@router.post("/freshness/run")
async def freshness_run(registry: SourceRegistry = Depends(get_registry)) -> dict[str, Any]:
    due = registry.freshness_due()
    refreshed = 0
    errors = []
    for sid in due:
        try:
            registry.fetch_and_parse(sid, actor="freshness_scheduler")
            refreshed += 1
        except SourceError as exc:
            errors.append({"source_id": str(sid), "code": exc.code})
    return {"due": len(due), "refreshed": refreshed, "errors": errors}
