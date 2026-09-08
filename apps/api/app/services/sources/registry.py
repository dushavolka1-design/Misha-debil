from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.services.sources.url_policy import (
    AllowlistConfig,
    UrlPolicyError,
    extract_text_no_js,
    load_allowlist,
    validate_redirect_chain,
    validate_url,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class SourceState(StrEnum):
    DISCOVERED = "discovered"
    FETCHED = "fetched"
    PARSED = "parsed"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    REJECTED = "rejected"


TERMINAL_OK = frozenset({SourceState.APPROVED, SourceState.SUPERSEDED, SourceState.EXPIRED})


TRANSITIONS: dict[SourceState, frozenset[SourceState]] = {
    SourceState.DISCOVERED: frozenset({SourceState.FETCHED, SourceState.REJECTED}),
    SourceState.FETCHED: frozenset({SourceState.PARSED, SourceState.REJECTED}),
    SourceState.PARSED: frozenset({SourceState.AWAITING_REVIEW, SourceState.REJECTED}),
    SourceState.AWAITING_REVIEW: frozenset(
        {SourceState.APPROVED, SourceState.REJECTED, SourceState.AWAITING_REVIEW},
    ),
    SourceState.APPROVED: frozenset({SourceState.SUPERSEDED, SourceState.EXPIRED}),
    SourceState.SUPERSEDED: frozenset(),
    SourceState.EXPIRED: frozenset(),
    SourceState.REJECTED: frozenset(),
}


class SourceError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class DomainSeed:
    host: str
    organ: str
    criticality: str
    fetch_interval_hours: int
    official_url: str


@dataclass
class SnapshotRecord:
    id: UUID
    source_id: UUID
    state: SourceState
    requested_url: str
    final_url: str
    content_hash: str
    raw: bytes
    headers: dict[str, str]
    fetched_at: datetime
    extracted_text: str
    parser_version: str
    valid_from: date | None = None
    valid_to: date | None = None
    act_title: str | None = None
    act_number: str | None = None
    act_date: date | None = None
    organ: str | None = None
    reviewer_id: str | None = None
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    link_status: str = "ok"  # ok|broken|stale
    etag: str | None = None
    last_modified: str | None = None
    previous_snapshot_id: UUID | None = None
    immutable: bool = True


@dataclass
class SourceRecordMem:
    id: UUID
    slug: str
    title: str
    organ: str
    official_url: str
    host: str
    criticality: str
    fetch_interval_hours: int
    state: SourceState = SourceState.DISCOVERED
    snapshots: list[UUID] = field(default_factory=list)
    dependent_norm_ids: list[str] = field(default_factory=list)
    dependent_form_ids: list[str] = field(default_factory=list)


@dataclass
class ReviewTask:
    id: UUID
    source_id: UUID
    snapshot_id: UUID
    reason: str
    created_at: datetime
    resolved_at: datetime | None = None
    status: str = "open"  # open|resolved


@dataclass
class AuditEvent:
    id: UUID
    at: datetime
    actor: str
    action: str
    source_id: UUID | None
    snapshot_id: UUID | None
    detail: dict[str, Any]


@dataclass
class FetchResult:
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    redirect_chain: list[str]


FetchFn = Callable[[str, dict[str, str]], FetchResult]


class SourceRegistry:
    def __init__(self, *, allowlist: AllowlistConfig | None = None, fetch_fn: FetchFn | None = None) -> None:
        self.cfg = allowlist or load_allowlist()
        self.fetch_fn = fetch_fn
        self.sources: dict[UUID, SourceRecordMem] = {}
        self.by_slug: dict[str, UUID] = {}
        self.snapshots: dict[UUID, SnapshotRecord] = {}
        self.review_tasks: list[ReviewTask] = []
        self.audit: list[AuditEvent] = []
        self.norms_status: dict[str, str] = {}  # norm_id -> approved|review
        self.forms_status: dict[str, str] = {}

    def _audit(
        self, actor: str, action: str, *, source_id: UUID | None = None, snapshot_id: UUID | None = None, **detail: Any
    ) -> None:
        self.audit.append(
            AuditEvent(
                id=uuid4(),
                at=utcnow(),
                actor=actor,
                action=action,
                source_id=source_id,
                snapshot_id=snapshot_id,
                detail=detail,
            ),
        )

    def seed_from_allowlist(self) -> list[SourceRecordMem]:
        """Seed only official domain metadata — no norms/deadlines from memory."""
        created = []
        for rule in self.cfg.hosts:
            slug = rule.host.replace(".", "-")
            if slug in self.by_slug:
                continue
            url = f"https://{rule.host}/"
            src = SourceRecordMem(
                id=uuid4(),
                slug=slug,
                title=f"Official domain: {rule.host}",
                organ=rule.organ,
                official_url=url,
                host=rule.host,
                criticality=rule.criticality,
                fetch_interval_hours=rule.fetch_interval_hours,
                state=SourceState.DISCOVERED,
            )
            self.sources[src.id] = src
            self.by_slug[slug] = src.id
            self._audit("system", "seed_domain", source_id=src.id, host=rule.host)
            created.append(src)
        return created

    def discover(
        self, *, slug: str, title: str, official_url: str, organ: str, actor: str = "editor"
    ) -> SourceRecordMem:
        try:
            canonical = validate_url(official_url, cfg=self.cfg)
        except UrlPolicyError as exc:
            raise SourceError(exc.code, exc.message, http_status=400) from exc
        host = canonical.split("/")[2]
        src = SourceRecordMem(
            id=uuid4(),
            slug=slug,
            title=title,
            organ=organ,
            official_url=canonical,
            host=host,
            criticality="medium",
            fetch_interval_hours=72,
            state=SourceState.DISCOVERED,
        )
        self.sources[src.id] = src
        self.by_slug[slug] = src.id
        self._audit(actor, "discovered", source_id=src.id, url=canonical)
        return src

    def _transition(self, snap: SnapshotRecord, target: SourceState) -> None:
        allowed = TRANSITIONS.get(snap.state, frozenset())
        if target not in allowed:
            raise SourceError("invalid_transition", f"{snap.state} -> {target}")
        snap.state = target

    def fetch_and_parse(
        self,
        source_id: UUID,
        *,
        actor: str = "fetcher",
        conditional: bool = True,
    ) -> SnapshotRecord:
        src = self.sources.get(source_id)
        if not src:
            raise SourceError("not_found", "Source not found", http_status=404)
        try:
            url = validate_url(src.official_url, cfg=self.cfg)
        except UrlPolicyError as exc:
            src.state = SourceState.DISCOVERED
            raise SourceError(exc.code, exc.message) from exc

        headers: dict[str, str] = {
            "User-Agent": "DAR-OfficialFetcher/1.0",
            "Accept": "text/html,application/pdf,text/plain",
        }
        prev = self.latest_snapshot(source_id)
        if conditional and prev:
            if prev.etag:
                headers["If-None-Match"] = prev.etag
            if prev.last_modified:
                headers["If-Modified-Since"] = prev.last_modified

        if not self.fetch_fn:
            raise SourceError("fetcher_unavailable", "No fetcher configured", http_status=503)

        result = self.fetch_fn(url, headers)
        # Validate redirect chain (deny-by-default)
        chain = result.redirect_chain or [result.final_url]
        try:
            final = validate_redirect_chain(chain, cfg=self.cfg)
        except UrlPolicyError as exc:
            raise SourceError(exc.code, exc.message, http_status=400) from exc

        if result.status_code == 304 and prev:
            prev.link_status = "ok"
            self._audit(actor, "not_modified", source_id=source_id, snapshot_id=prev.id)
            return prev

        if result.status_code >= 400:
            snap = SnapshotRecord(
                id=uuid4(),
                source_id=source_id,
                state=SourceState.FETCHED,
                requested_url=url,
                final_url=final,
                content_hash="",
                raw=b"",
                headers=dict(result.headers),
                fetched_at=utcnow(),
                extracted_text="",
                parser_version="html.strip.v1",
                link_status="broken",
                organ=src.organ,
                previous_snapshot_id=prev.id if prev else None,
            )
            # Mark broken visibly
            self.snapshots[snap.id] = snap
            src.snapshots.append(snap.id)
            self._audit(actor, "fetch_broken", source_id=source_id, snapshot_id=snap.id, status=result.status_code)
            raise SourceError("fetch_broken", f"Upstream returned {result.status_code}", http_status=502)

        if len(result.body) > self.cfg.max_bytes:
            raise SourceError("too_large", "Response exceeds max size")

        ctype = (
            (result.headers.get("content-type") or result.headers.get("Content-Type") or "")
            .split(";")[0]
            .strip()
            .lower()
        )
        if self.cfg.allowed_content_types and ctype and ctype not in self.cfg.allowed_content_types:
            raise SourceError("content_type_denied", f"Content-Type not allowed: {ctype}")

        digest = hashlib.sha256(result.body).hexdigest()
        text, parser_v = extract_text_no_js(result.body, content_type=ctype or "text/html")

        snap = SnapshotRecord(
            id=uuid4(),
            source_id=source_id,
            state=SourceState.DISCOVERED,
            requested_url=url,
            final_url=final,
            content_hash=digest,
            raw=result.body,
            headers={k.lower(): v for k, v in result.headers.items()},
            fetched_at=utcnow(),
            extracted_text=text,
            parser_version=parser_v,
            organ=src.organ,
            etag=result.headers.get("etag") or result.headers.get("ETag"),
            last_modified=result.headers.get("last-modified") or result.headers.get("Last-Modified"),
            previous_snapshot_id=prev.id if prev else None,
            link_status="ok",
        )
        # FSM: discovered->fetched->parsed->awaiting_review
        snap.state = SourceState.DISCOVERED
        self._transition(snap, SourceState.FETCHED)
        self._transition(snap, SourceState.PARSED)
        self._transition(snap, SourceState.AWAITING_REVIEW)
        self.snapshots[snap.id] = snap
        src.snapshots.append(snap.id)
        src.state = SourceState.AWAITING_REVIEW

        if prev and prev.state == SourceState.APPROVED and prev.content_hash != digest:
            task = ReviewTask(
                id=uuid4(),
                source_id=source_id,
                snapshot_id=snap.id,
                reason="content_hash_changed",
                created_at=utcnow(),
            )
            self.review_tasks.append(task)
            # Dependents immediately to review
            for nid in src.dependent_norm_ids:
                self.norms_status[nid] = "review"
            for fid in src.dependent_form_ids:
                self.forms_status[fid] = "review"
            self._audit(
                actor, "hash_change_review_task", source_id=source_id, snapshot_id=snap.id, task_id=str(task.id)
            )

        self._audit(actor, "fetched_parsed", source_id=source_id, snapshot_id=snap.id, content_hash=digest)
        return snap

    def latest_snapshot(self, source_id: UUID) -> SnapshotRecord | None:
        src = self.sources.get(source_id)
        snaps = src.get("snapshots") if isinstance(src, dict) else getattr(src, "snapshots", None)
        if not src or not snaps:
            return None
        last = snaps[-1]
        rec = self.snapshots.get(last)
        if rec is None:
            rec = self.snapshots.get(UUID(str(last)))
        return rec

    def approved_snapshot(self, source_id: UUID) -> SnapshotRecord | None:
        src = self.sources.get(source_id)
        snaps = src.get("snapshots") if isinstance(src, dict) else getattr(src, "snapshots", None)
        if not src or not snaps:
            return None
        for sid in reversed(list(snaps)):
            snap = self.snapshots.get(sid) or self.snapshots.get(UUID(str(sid)))
            if not snap:
                continue
            state = snap.get("state") if isinstance(snap, dict) else getattr(snap, "state", None)
            if str(state) == SourceState.APPROVED.value:
                return snap
        return None

    def production_basis_visible(self, snapshot_id: UUID) -> bool:
        snap = self.snapshots.get(snapshot_id)
        return bool(snap and snap.state == SourceState.APPROVED)

    def diff_snapshots(self, old_id: UUID, new_id: UUID) -> dict[str, Any]:
        old, new = self.snapshots[old_id], self.snapshots[new_id]
        return {
            "old_hash": old.content_hash,
            "new_hash": new.content_hash,
            "hash_changed": old.content_hash != new.content_hash,
            "old_fetched_at": old.fetched_at.isoformat(),
            "new_fetched_at": new.fetched_at.isoformat(),
            "old_final_url": old.final_url,
            "new_final_url": new.final_url,
            "old_act": {
                "title": old.act_title,
                "number": old.act_number,
                "date": old.act_date.isoformat() if old.act_date else None,
            },
            "new_act": {
                "title": new.act_title,
                "number": new.act_number,
                "date": new.act_date.isoformat() if new.act_date else None,
            },
            "text_preview_old": old.extracted_text[:240],
            "text_preview_new": new.extracted_text[:240],
        }

    def approve(
        self,
        snapshot_id: UUID,
        *,
        actor: str,
        comment: str,
        valid_from: date | None = None,
        valid_to: date | None = None,
        act_title: str | None = None,
        act_number: str | None = None,
        act_date: date | None = None,
    ) -> SnapshotRecord:
        snap = self.snapshots.get(snapshot_id)
        if not snap:
            raise SourceError("not_found", "Snapshot not found", http_status=404)
        if snap.state != SourceState.AWAITING_REVIEW:
            raise SourceError("not_awaiting_review", "Snapshot is not awaiting review")
        # Supersede previous approved
        prev_approved = self.approved_snapshot(snap.source_id)
        if prev_approved and prev_approved.id != snap.id:
            prev_approved.state = SourceState.SUPERSEDED
            self._audit(actor, "superseded", source_id=snap.source_id, snapshot_id=prev_approved.id)
        snap.valid_from = valid_from
        snap.valid_to = valid_to
        snap.act_title = act_title
        snap.act_number = act_number
        snap.act_date = act_date
        snap.reviewer_id = actor
        snap.review_comment = comment
        snap.reviewed_at = utcnow()
        self._transition(snap, SourceState.APPROVED)
        self.sources[snap.source_id].state = SourceState.APPROVED
        for t in self.review_tasks:
            if t.snapshot_id == snapshot_id and t.status == "open":
                t.status = "resolved"
                t.resolved_at = utcnow()
        self._audit(actor, "approved", source_id=snap.source_id, snapshot_id=snap.id, comment=comment)
        return snap

    def reject(self, snapshot_id: UUID, *, actor: str, comment: str) -> SnapshotRecord:
        snap = self.snapshots.get(snapshot_id)
        if not snap:
            raise SourceError("not_found", "Snapshot not found", http_status=404)
        snap.reviewer_id = actor
        snap.review_comment = comment
        snap.reviewed_at = utcnow()
        self._transition(snap, SourceState.REJECTED)
        self._audit(actor, "rejected", source_id=snap.source_id, snapshot_id=snap.id, comment=comment)
        return snap

    def applicable_on(self, snapshot_id: UUID, on: date) -> bool:
        """Do not auto-substitute current edition for historical dates."""
        snap = self.snapshots.get(snapshot_id)
        if not snap or snap.state != SourceState.APPROVED:
            return False
        if snap.valid_from and on < snap.valid_from:
            return False
        if snap.valid_to and on > snap.valid_to:
            return False
        return True

    def citation(
        self,
        snapshot_id: UUID,
        *,
        quote: str,
        on_date: date,
    ) -> dict[str, Any]:
        snap = self.snapshots.get(snapshot_id)
        if not snap:
            raise SourceError("not_found", "Snapshot not found", http_status=404)
        verified = snap.state == SourceState.APPROVED and self.applicable_on(snapshot_id, on_date)
        # Unapproved never presented as production basis
        if snap.state != SourceState.APPROVED:
            return {
                "usable_as_basis": False,
                "reason": "snapshot_not_approved",
                "state": snap.state.value,
                "link_status": snap.link_status,
            }
        if not self.applicable_on(snapshot_id, on_date):
            return {
                "usable_as_basis": False,
                "reason": "not_applicable_on_date",
                "state": snap.state.value,
                "valid_from": snap.valid_from.isoformat() if snap.valid_from else None,
                "valid_to": snap.valid_to.isoformat() if snap.valid_to else None,
                "requested_on": on_date.isoformat(),
            }
        return {
            "usable_as_basis": True,
            "organ": snap.organ or self.sources[snap.source_id].organ,
            "document": snap.act_title or self.sources[snap.source_id].title,
            "number": snap.act_number,
            "date": snap.act_date.isoformat() if snap.act_date else None,
            "quote": quote,
            "official_url": snap.final_url,
            "verified": verified,
            "applicable_on": on_date.isoformat(),
            "snapshot_id": str(snap.id),
            "content_hash": snap.content_hash,
            "link_status": snap.link_status,
            "reviewed_by": snap.reviewer_id,
            "reviewed_at": snap.reviewed_at.isoformat() if snap.reviewed_at else None,
        }

    def freshness_due(self, now: datetime | None = None) -> list[UUID]:
        now = now or utcnow()
        due = []
        for src in self.sources.values():
            snap = self.latest_snapshot(src.id)
            if not snap:
                due.append(src.id)
                continue
            interval = timedelta(hours=src.fetch_interval_hours)
            # grace: criticality high = 6h grace already in interval; mark stale after 1.5x
            if snap.fetched_at + interval < now:
                if snap.fetched_at + interval * 1.5 < now:
                    snap.link_status = "stale"
                due.append(src.id)
        return due

    def bind_dependent(self, source_id: UUID, *, norm_id: str | None = None, form_id: str | None = None) -> None:
        src = self.sources[source_id]
        if norm_id:
            src.dependent_norm_ids.append(norm_id)
            self.norms_status[norm_id] = "approved" if self.approved_snapshot(source_id) else "review"
        if form_id:
            src.dependent_form_ids.append(form_id)
            self.forms_status[form_id] = "approved" if self.approved_snapshot(source_id) else "review"
