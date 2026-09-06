from __future__ import annotations

import json
import logging
from dataclasses import asdict, fields
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import delete, select, text

from app.models import (
    AnalysisRun,
    AppStateBlob,
    ConsentEvent,
    Document,
    DocumentFile,
    LegalDocument,
    Session,
    User,
)
from app.persistence.form_catalog_codec import (
    CatalogPersistenceError,
    catalog_fatal,
    form_record_from_mapping,
    form_record_to_payload,
)
from app.persistence.serde import persistence_dumps, persistence_loads
from app.persistence.sync_db import get_sync_engine, sync_session
from app.services.analysis.pipeline import AnalysisRunRecord, AnalysisStatus, AnalysisStore, ProgressEvent
from app.services.analysis.records import FindingRecord, PageRecord
from app.services.auth_consent import (
    AuthConsentStore,
    ConsentAction,
    ConsentEventRecord,
    LegalDoc,
    PublicationStatus,
    SessionRecord,
    UserRecord,
)
from app.services.forms.catalog import FormRecord
from app.services.sources.registry import SnapshotRecord, SourceRecordMem, SourceState
from app.services.upload.fsm import DocumentState
from app.services.upload.lifecycle import DocumentRecord, DocumentStore, StoredBlobMeta
from app.settings import get_settings

logger = logging.getLogger(__name__)

DirtyCallback = Callable[[], None]


class WriteThroughDict(dict):
    """Dict that invokes a callback after each mutation (for DB write-through)."""

    def __init__(self, on_change: DirtyCallback, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._on_change = on_change

    def __setitem__(self, key: Any, value: Any) -> None:
        super().__setitem__(key, value)
        self._on_change()

    def __delitem__(self, key: Any) -> None:
        super().__delitem__(key)
        self._on_change()


class DirtyFlag:
    def __init__(self) -> None:
        self.dirty = False

    def mark(self) -> None:
        self.dirty = True

    def clear(self) -> bool:
        was = self.dirty
        self.dirty = False
        return was


_persistence_flags: dict[str, DirtyFlag] = {}


def _dialect_insert(table: Any):
    """PostgreSQL or SQLite upsert insert — production stays on PostgreSQL."""
    url = str(get_sync_engine().url)
    if url.startswith("sqlite"):
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    return dialect_insert(table)


def _flag(name: str) -> DirtyFlag:
    return _persistence_flags.setdefault(name, DirtyFlag())


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return _aware(dt)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _record_from_dict(cls: type, data: dict[str, Any]) -> Any:
    field_names = {f.name for f in fields(cls)}
    kwargs = {}
    for name in field_names:
        if name not in data:
            continue
        val = data[name]
        if name.endswith("_id") or name in {
            "id",
            "user_id",
            "tenant_id",
            "document_id",
            "rotated_from",
            "supersedes_id",
            "legal_document_id",
            "subject_user_id",
        }:
            if val is not None and not isinstance(val, UUID):
                val = UUID(str(val))
        if name in {
            "expires_at",
            "revoked_at",
            "created_at",
            "updated_at",
            "effective_at",
            "occurred_at",
            "email_verified_at",
            "upload_token_expires",
            "tombstone_at",
            "retention_expires_at",
            "used_at",
            "fetched_at",
            "reviewed_at",
        }:
            if isinstance(val, str):
                val = _parse_dt(val)
        if name in {"valid_from", "valid_to", "act_date"} and isinstance(val, str):
            parsed = _parse_dt(val)
            val = parsed.date() if parsed else None
        if name == "state" and cls is DocumentRecord:
            val = DocumentState(val)
        if name == "state" and cls in {SourceRecordMem, SnapshotRecord}:
            val = SourceState(val)
        if name == "snapshots" and isinstance(val, list):
            val = [UUID(str(x)) if not isinstance(x, UUID) else x for x in val]
        if name == "status" and cls is AnalysisRunRecord:
            val = AnalysisStatus(val)
        if name == "pages" and cls is AnalysisRunRecord and isinstance(val, list):
            val = [PageRecord(**p) if isinstance(p, dict) else p for p in val]
        if name == "findings" and cls is AnalysisRunRecord and isinstance(val, list):
            restored_findings = []
            for finding in val:
                if not isinstance(finding, dict):
                    restored_findings.append(finding)
                    continue
                item = dict(finding)
                if item.get("id") is not None and not isinstance(item["id"], UUID):
                    item["id"] = UUID(str(item["id"]))
                restored_findings.append(FindingRecord(**item))
            val = restored_findings
        if name == "progress" and cls is AnalysisRunRecord and isinstance(val, list):
            restored_progress = []
            for event in val:
                if not isinstance(event, dict):
                    restored_progress.append(event)
                    continue
                item = dict(event)
                if isinstance(item.get("at"), str):
                    item["at"] = _parse_dt(item["at"])
                restored_progress.append(ProgressEvent(**item))
            val = restored_progress
        if name == "publication_status" and cls is LegalDoc:
            val = PublicationStatus(val)
        if name == "action" and cls is ConsentEventRecord:
            val = ConsentAction(val)
        if name == "blobs" and isinstance(val, dict):
            restored_blobs: dict[str, Any] = {}
            for blob_key, blob_val in val.items():
                if not isinstance(blob_val, dict):
                    restored_blobs[blob_key] = blob_val
                    continue
                blob = dict(blob_val)
                for dt_key in ("erased_at", "expires_at"):
                    if isinstance(blob.get(dt_key), str):
                        blob[dt_key] = _parse_dt(blob[dt_key])
                restored_blobs[blob_key] = StoredBlobMeta(**blob)
            val = restored_blobs
        if name == "processed_jobs" and isinstance(val, list):
            val = set(val)
        kwargs[name] = val
    return cls(**kwargs)


# --- Auth persistence ---


def _save_user(user: UserRecord) -> None:
    with sync_session() as session:
        stmt = _dialect_insert(User).values(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            status=user.status,
            email_verified_at=user.email_verified_at,
            display_name=user.display_name or None,
            avatar_jpeg=user.avatar_jpeg,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[User.id],
            set_={
                "email": user.email,
                "password_hash": user.password_hash,
                "role": user.role,
                "status": user.status,
                "email_verified_at": user.email_verified_at,
                "display_name": user.display_name or None,
                "avatar_jpeg": user.avatar_jpeg,
            },
        )
        session.execute(stmt)
        session.commit()


def _save_session(sess: SessionRecord) -> None:
    with sync_session() as session:
        stmt = _dialect_insert(Session).values(
            id=sess.id,
            user_id=sess.user_id,
            tenant_id=sess.tenant_id,
            token_hash=sess.token_hash,
            expires_at=sess.expires_at,
            revoked_at=sess.revoked_at,
            rotated_from=sess.rotated_from,
            user_agent=sess.user_agent,
            ip=sess.ip,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Session.id],
            set_={
                "expires_at": sess.expires_at,
                "revoked_at": sess.revoked_at,
                "token_hash": sess.token_hash,
            },
        )
        session.execute(stmt)
        session.commit()


def _save_legal(doc: LegalDoc) -> None:
    with sync_session() as session:
        stmt = _dialect_insert(LegalDocument).values(
            id=doc.id,
            consent_id=doc.consent_id,
            consent_version=doc.consent_version,
            locale=doc.locale,
            content_hash=doc.content_hash,
            body_path=doc.body_path,
            canonical_text=doc.canonical_text,
            effective_from=doc.effective_at,
            supersedes_id=doc.supersedes_id,
            reviewer_id=doc.reviewer_id,
            review_status="published",
            publication_status=doc.publication_status.value,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[LegalDocument.id],
            set_={"publication_status": doc.publication_status.value},
        )
        session.execute(stmt)
        session.commit()


def _save_consent_event(event: ConsentEventRecord) -> None:
    with sync_session() as session:
        exists = session.get(ConsentEvent, event.id)
        if exists:
            return
        row = ConsentEvent(
            id=event.id,
            user_id=event.subject_user_id,
            tenant_id=UUID(int=0),  # filled from user if needed
            legal_document_id=event.legal_document_id,
            consent_id=event.consent_id,
            consent_version=event.consent_version,
            content_hash=event.content_hash,
            action=event.action.value,
            accepted_at=event.occurred_at,
            occurred_at=event.occurred_at,
            ip=event.ip,
            user_agent=event.user_agent,
            locale=event.locale,
            request_id=event.request_id,
            evidence_schema_version=event.evidence_schema_version,
            evidence={},
        )
        user = session.get(User, event.subject_user_id)
        if user:
            row.tenant_id = user.tenant_id
        session.add(row)
        session.commit()


def _load_auth_store(store: AuthConsentStore) -> None:
    with sync_session() as session:
        for row in session.scalars(select(User)).all():
            user = UserRecord(
                id=row.id,
                tenant_id=row.tenant_id,
                email=row.email,
                password_hash=row.password_hash or "",
                role=row.role,
                status=row.status,
                email_verified_at=_aware(row.email_verified_at),
                created_at=_aware(row.created_at) or row.created_at,
                display_name=getattr(row, "display_name", None) or "",
                avatar_jpeg=getattr(row, "avatar_jpeg", None),
            )
            store.index_user(user)
        for row in session.scalars(select(Session)).all():
            sess = SessionRecord(
                id=row.id,
                user_id=row.user_id,
                tenant_id=row.tenant_id,
                token_hash=row.token_hash,
                expires_at=_aware(row.expires_at) or row.expires_at,
                revoked_at=_aware(row.revoked_at),
                rotated_from=row.rotated_from,
                user_agent=row.user_agent,
                ip=row.ip,
            )
            store.sessions[sess.id] = sess
            store.sessions_by_token[sess.token_hash] = sess.id
        for row in session.scalars(select(LegalDocument)).all():
            doc = LegalDoc(
                id=row.id,
                consent_id=row.consent_id,
                consent_version=row.consent_version,
                locale=row.locale,
                canonical_text=row.canonical_text or "",
                content_hash=row.content_hash,
                effective_at=_aware(row.effective_from) or row.effective_from,
                supersedes_id=row.supersedes_id,
                reviewer_id=row.reviewer_id,
                publication_status=PublicationStatus(row.publication_status),
                body_path=row.body_path,
                immutable=row.publication_status in {"published", "retired"},
            )
            store.legal[doc.id] = doc
        for row in session.scalars(select(ConsentEvent)).all():
            event = ConsentEventRecord(
                id=row.id,
                subject_user_id=row.user_id,
                legal_document_id=row.legal_document_id,
                consent_id=row.consent_id or "",
                consent_version=row.consent_version or "",
                content_hash=row.content_hash or "",
                action=ConsentAction(row.action),
                occurred_at=_aware(row.occurred_at or row.accepted_at) or row.accepted_at,
                ip=row.ip,
                user_agent=row.user_agent,
                locale=row.locale,
                request_id=row.request_id or "",
                evidence_schema_version=row.evidence_schema_version,
            )
            store.consent_events.append(event)
    blob = _load_blob("auth", "email_tokens")
    if blob:
        from app.services.auth_consent import EmailToken

        store.email_tokens = [_record_from_dict(EmailToken, item) for item in blob]


def _persist_auth_store(store: AuthConsentStore) -> None:
    for user in store.users.values():
        _save_user(user)
    for sess in store.sessions.values():
        _save_session(sess)
    for doc in store.legal.values():
        _save_legal(doc)
    for event in store.consent_events:
        _save_consent_event(event)
    _save_blob("auth", "email_tokens", [asdict(t) for t in store.email_tokens])


# --- Document persistence ---


def _to_sql_json(value: Any) -> Any:
    """JSON column payload: UUIDs, datetimes, bytes, enums become JSON-safe."""
    return json.loads(persistence_dumps(value))


def _from_sql_json(value: Any) -> Any:
    if not value:
        return {}
    return persistence_loads(json.dumps(value))


def _doc_runtime(doc: DocumentRecord) -> dict[str, Any]:
    data = asdict(doc)
    for key in ("id", "user_id", "tenant_id", "display_name", "state"):
        data.pop(key, None)
    return _to_sql_json(data)


def _save_document(doc: DocumentRecord) -> None:
    runtime = _doc_runtime(doc)
    with sync_session() as session:
        stmt = _dialect_insert(Document).values(
            id=doc.id,
            user_id=doc.user_id,
            tenant_id=doc.tenant_id,
            display_name=doc.display_name,
            document_type=doc.detected_type or "unknown",
            detected_type=doc.detected_type,
            status=doc.state.value,
            error_code=doc.error_code,
            idempotency_key=doc.idempotency_key,
            retention_expires_at=doc.retention_expires_at,
            tombstone_at=doc.tombstone_at,
            legal_hold=doc.legal_hold,
            runtime_json=runtime,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Document.id],
            set_={
                "status": doc.state.value,
                "display_name": doc.display_name,
                "error_code": doc.error_code,
                "runtime_json": runtime,
                "tombstone_at": doc.tombstone_at,
            },
        )
        session.execute(stmt)
        session.commit()


def _load_documents(store: DocumentStore) -> None:
    with sync_session() as session:
        for row in session.scalars(select(Document)).all():
            runtime = dict(_from_sql_json(row.runtime_json) or {})
            runtime.update(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "tenant_id": row.tenant_id,
                    "display_name": row.display_name or "",
                    "state": row.status,
                },
            )
            doc = _record_from_dict(DocumentRecord, runtime)
            store.documents[doc.id] = doc
            if doc.idempotency_key:
                store.by_idempotency[(doc.user_id, doc.idempotency_key)] = doc.id


def _persist_documents(store: DocumentStore) -> None:
    for doc in store.documents.values():
        _save_document(doc)
    _save_blob(
        "documents",
        "meta",
        {
            "by_idempotency": {f"{uid}:{key}": str(did) for (uid, key), did in store.by_idempotency.items()},
            "uploads_today": {f"{uid}:{day}": count for (uid, day), count in store.uploads_today.items()},
        },
    )


def _load_document_meta(store: DocumentStore) -> None:
    blob = _load_blob("documents", "meta")
    if not blob:
        return
    for key, did in blob.get("by_idempotency", {}).items():
        uid_s, idem = key.split(":", 1)
        store.by_idempotency[(UUID(uid_s), idem)] = UUID(str(did))
    for key, count in blob.get("uploads_today", {}).items():
        uid_s, day = key.split(":", 1)
        store.uploads_today[(UUID(uid_s), day)] = int(count)


# --- Analysis persistence ---


def _save_analysis_run(run: AnalysisRunRecord) -> None:
    runtime = _to_sql_json(asdict(run))
    for key in ("id", "document_id", "user_id", "tenant_id", "status"):
        runtime.pop(key, None)
    with sync_session() as session:
        stmt = _dialect_insert(AnalysisRun).values(
            id=run.id,
            document_id=run.document_id,
            user_id=run.user_id,
            tenant_id=run.tenant_id,
            status=run.status.value,
            pipeline_version=run.pipeline_version,
            prompt_version=run.prompt_version,
            schema_version=run.schema_version,
            provider_ocr=run.ocr_provider,
            ocr_model_version=run.ocr_model_version,
            provider_llm=run.llm_provider,
            llm_model_version=run.llm_model_version,
            error_code=run.error_code,
            runtime_json=runtime,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AnalysisRun.id],
            set_={"status": run.status.value, "error_code": run.error_code, "runtime_json": runtime},
        )
        session.execute(stmt)
        session.commit()


def _load_analysis(store: AnalysisStore) -> None:
    with sync_session() as session:
        for row in session.scalars(select(AnalysisRun)).all():
            runtime = dict(_from_sql_json(row.runtime_json) or {})
            runtime.update(
                {
                    "id": row.id,
                    "document_id": row.document_id,
                    "user_id": row.user_id,
                    "tenant_id": row.tenant_id,
                    "status": row.status,
                    "pipeline_version": row.pipeline_version or "",
                    "prompt_version": row.prompt_version or "",
                    "schema_version": row.schema_version or "",
                    "ocr_provider": row.provider_ocr or "",
                    "ocr_model_version": row.ocr_model_version or "",
                    "llm_provider": row.provider_llm or "",
                    "llm_model_version": row.llm_model_version or "",
                    "error_code": row.error_code,
                },
            )
            run = _record_from_dict(AnalysisRunRecord, runtime)
            store.runs[run.id] = run
            store.by_document.setdefault(run.document_id, []).append(run.id)
    blob = _load_blob("analysis", "by_document_extra")
    if blob:
        for doc_id, run_ids in blob.items():
            store.by_document.setdefault(UUID(doc_id), [])
            for rid in run_ids:
                uid = UUID(rid)
                if uid not in store.by_document[UUID(doc_id)]:
                    store.by_document[UUID(doc_id)].append(uid)


def _persist_analysis(store: AnalysisStore) -> None:
    keep_ids = set(store.runs.keys())
    with sync_session() as session:
        stale = [row for row in session.scalars(select(AnalysisRun.id)).all() if row not in keep_ids]
        if stale:
            session.execute(delete(AnalysisRun).where(AnalysisRun.id.in_(stale)))
            session.commit()
    for run in store.runs.values():
        _save_analysis_run(run)
    _save_blob(
        "analysis",
        "by_document_extra",
        {str(k): [str(r) for r in v] for k, v in store.by_document.items()},
    )


def delete_analysis_runs_for_document(document_id: UUID) -> None:
    with sync_session() as session:
        session.execute(delete(AnalysisRun).where(AnalysisRun.document_id == document_id))
        session.commit()


# --- Generic blob persistence for remaining stores ---


def _save_blob(namespace: str, blob_key: str, value: Any) -> None:
    payload = json.loads(persistence_dumps(value))
    with sync_session() as session:
        stmt = _dialect_insert(AppStateBlob).values(
            namespace=namespace,
            blob_key=blob_key,
            value_json=payload,
            updated_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["namespace", "blob_key"],
            set_={
                "value_json": stmt.excluded.value_json,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        session.execute(stmt)
        session.commit()


def _load_blob(namespace: str, blob_key: str) -> Any | None:
    with sync_session() as session:
        row = session.execute(
            text("SELECT value_json FROM app_state_blobs WHERE namespace = :ns AND blob_key = :key"),
            {"ns": namespace, "key": blob_key},
        ).first()
        if not row:
            return None
        val = row[0]
        if val is None:
            return None
        if isinstance(val, str):
            return persistence_loads(val)
        return persistence_loads(json.dumps(val))


def _serialize_store(namespace: str, store: Any, attr: str) -> None:
    value = getattr(store, attr)
    if namespace == "forms" and attr == "forms" and isinstance(value, dict):
        payload = {str(k): form_record_to_payload(v) if isinstance(v, FormRecord) else v for k, v in value.items()}
    elif isinstance(value, dict):
        payload = {str(k): asdict(v) if hasattr(v, "__dataclass_fields__") else v for k, v in value.items()}
    elif isinstance(value, list):
        payload = [asdict(v) if hasattr(v, "__dataclass_fields__") else v for v in value]
    else:
        payload = value
    _save_blob(namespace, attr, payload)


def _deserialize_store(namespace: str, store: Any, attr: str, cls: type | None = None) -> None:
    payload = _load_blob(namespace, attr)
    if payload is None:
        return
    if namespace == "sources" and attr == "sources" and isinstance(payload, dict):
        restored_sources: dict[Any, SourceRecordMem] = {}
        for key, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            try:
                rec = _record_from_dict(SourceRecordMem, raw)
            except Exception:
                continue
            restored_sources[rec.id] = rec
            if hasattr(store, "by_slug"):
                store.by_slug[rec.slug] = rec.id
        store.sources = restored_sources
        return
    if namespace == "sources" and attr == "snapshots" and isinstance(payload, dict):
        restored_snaps: dict[Any, SnapshotRecord] = {}
        for key, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            try:
                rec = _record_from_dict(SnapshotRecord, raw)
            except Exception:
                continue
            restored_snaps[rec.id] = rec
        store.snapshots = restored_snaps
        return
        restored: dict[Any, FormRecord] = {}
        for key, raw in payload.items():
            rec = form_record_from_mapping(key, raw)
            restored[rec.id] = rec
        store.forms = restored
        if hasattr(store, "rebuild_slug_index"):
            store.rebuild_slug_index()
        return
    if namespace == "forms" and attr == "by_slug" and isinstance(payload, dict):
        store.by_slug = {str(k): UUID(str(v)) for k, v in payload.items()}
        return
    if cls is FormRecord and isinstance(payload, dict):
        store.forms = {form_record_from_mapping(k, v).id: form_record_from_mapping(k, v) for k, v in payload.items()}
        store.rebuild_slug_index()
        return
    if cls and isinstance(payload, list):
        setattr(store, attr, [_record_from_dict(cls, item) for item in payload])
    elif cls and isinstance(payload, dict):
        setattr(store, attr, {UUID(k) if len(k) == 36 else k: _record_from_dict(cls, v) for k, v in payload.items()})
    else:
        setattr(store, attr, payload)


def _hydrate_form_fill(service: Any) -> None:
    from app.persistence.fill_runtime_repo import fill_runtime_tables_ready, load_fill_runtime

    if fill_runtime_tables_ready():
        versions, by_catalog, drafts, generated = load_fill_runtime()
        service.versions.update(versions)
        service.by_catalog.update(by_catalog)
        service.drafts.update(drafts)
        service.generated.update(generated)
        for rec in versions.values():
            service.by_slug_ver[(rec.slug, rec.form_version)] = rec.id
        service.enable_durable()
    if service.versions:
        return
    _load_form_fill_store(service)
    if fill_runtime_tables_ready():
        service.enable_durable()
        for rec in service.versions.values():
            service._persist_version(rec)
        for rec in service.drafts.values():
            service._persist_draft(rec)
        for rec in service.generated.values():
            service._persist_generated(rec)


def _load_catalog_store(app_state: Any) -> None:
    from app.persistence.form_catalog_repo import catalog_tables_ready, load_forms
    from app.scripts.repair_form_catalog import repair_form_catalog_blobs

    catalog = getattr(app_state, "form_catalog", None)
    fill = getattr(app_state, "form_fill", None)
    if catalog is None:
        return
    settings = get_settings()
    if not catalog_tables_ready():
        if settings.app_env in {"desktop", "production"}:
            raise catalog_fatal("catalog_schema_missing")
        return
    repair_form_catalog_blobs()
    forms, raw_store, isolated = load_forms()
    catalog.forms = forms
    catalog.raw_store = raw_store
    catalog.rebuild_slug_index()
    catalog.quarantine.extend(isolated)
    catalog.enable_persist()
    catalog.apply_invariants(
        fill_version_ids=set(fill.versions.keys()) if fill is not None else set(),
        snapshot_ids=set(getattr(getattr(app_state, "source_registry", None), "snapshots", {}).keys()),
    )


def load_persistence(app_state: Any) -> None:
    """Load durable state. Catalog failures fail readiness instead of leaving dicts in the store."""
    app_state.catalog_ok = False
    app_state.catalog_persistence_error = None
    settings = get_settings()
    try:
        with sync_session() as session:
            session.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("PostgreSQL unavailable — running without durable persistence: %s", exc)
        if settings.app_env == "desktop":
            err = catalog_fatal("catalog_database_unavailable")
            app_state.catalog_persistence_error = err.as_dict()
        return

    try:
        auth: AuthConsentStore = app_state.auth_store
        _load_auth_store(auth)

        doc: DocumentStore = app_state.doc_store
        _load_documents(doc)
        _load_document_meta(doc)

        analysis: AnalysisStore = app_state.analysis_store
        _load_analysis(analysis)

        for ns, store, attrs in _blob_store_specs(app_state):
            if ns == "form_fill":
                _hydrate_form_fill(store)
                continue
            if ns == "forms":
                continue
            for attr in attrs:
                _deserialize_store(ns, store, attr, None)
    except Exception as exc:
        logger.warning("Failed to load persistence layer (run alembic upgrade head): %s", exc)

    try:
        _load_catalog_store(app_state)
        catalog = getattr(app_state, "form_catalog", None)
        if catalog is None:
            app_state.catalog_ok = True
        else:
            app_state.catalog_ok = catalog.typed_catalog_ok()
    except CatalogPersistenceError as exc:
        app_state.catalog_persistence_error = exc.as_dict()
        app_state.catalog_ok = False
        logger.error("Catalog persistence failed code=%s correlation_id=%s", exc.code, exc.correlation_id)
    except Exception as exc:
        err = catalog_fatal("catalog_load_failed")
        app_state.catalog_persistence_error = err.as_dict()
        app_state.catalog_ok = False
        logger.error("Catalog persistence failed: %s", exc)


def attach_persistence(app_state: Any) -> None:
    """Wrap mutable dicts with write-through hooks."""

    def auth_users_change() -> None:
        _flag("auth").mark()

    auth: AuthConsentStore = app_state.auth_store
    auth.users = WriteThroughDict(auth_users_change, auth.users)
    auth.sessions = WriteThroughDict(auth_users_change, auth.sessions)
    auth.legal = WriteThroughDict(auth_users_change, auth.legal)

    original_append = auth.append_consent_event

    def append_and_mark(event: ConsentEventRecord) -> ConsentEventRecord:
        result = original_append(event)
        _flag("auth").mark()
        return result

    auth.append_consent_event = append_and_mark  # type: ignore[method-assign]

    doc: DocumentStore = app_state.doc_store

    def doc_change() -> None:
        _flag("documents").mark()

    doc.documents = WriteThroughDict(doc_change, doc.documents)

    analysis: AnalysisStore = app_state.analysis_store

    def analysis_change() -> None:
        _flag("analysis").mark()

    analysis.runs = WriteThroughDict(analysis_change, analysis.runs)

    form_fill = getattr(app_state, "form_fill", None)
    if form_fill is not None:

        def form_fill_coord_change() -> None:
            _flag("form_fill_coord").mark()

        form_fill.coord_drafts = WriteThroughDict(form_fill_coord_change, form_fill.coord_drafts)


def flush_persistence(app_state: Any) -> None:
    """Persist dirty stores to PostgreSQL."""
    try:
        if _flag("auth").clear():
            _persist_auth_store(app_state.auth_store)
        if _flag("documents").clear():
            _persist_documents(app_state.doc_store)
        if _flag("analysis").clear():
            _persist_analysis(app_state.analysis_store)
        for ns, store, attrs in _blob_store_specs(app_state):
            if ns in {"forms", "form_fill"}:
                continue
            if _flag(ns).clear():
                for attr in attrs:
                    _serialize_store(ns, store, attr)
        if _flag("form_fill_coord").clear() and getattr(app_state, "form_fill", None) is not None:
            _save_blob(
                "form_fill",
                "coord_drafts",
                {str(k): asdict(v) for k, v in app_state.form_fill.coord_drafts.items()},
            )
    except Exception as exc:
        logger.warning("Persistence flush skipped: %s", exc)


def _load_form_fill_store(service: Any) -> None:
    from datetime import date

    from app.services.forms.fill.coord_map import CoordField, CoordinateMap
    from app.services.forms.fill.service import (
        CoordMapDraft,
        FormDraftRecord,
        FormVersionRecord,
        GeneratedFormRecord,
    )

    versions_payload = _load_blob("form_fill", "versions")
    if isinstance(versions_payload, dict):
        for key, raw in versions_payload.items():
            if not isinstance(raw, dict):
                continue
            cmap_raw = raw.get("coord_map") or {}
            fields_raw = cmap_raw.get("fields") or []
            cmap = CoordinateMap(
                version=str(cmap_raw.get("version", "coord.v1")),
                page_count=int(cmap_raw.get("page_count", 1)),
                fields=[CoordField.from_dict(f) for f in fields_raw],
                page_boxes=cmap_raw.get("page_boxes") or [],
            )
            vid = UUID(str(key))
            rec = FormVersionRecord(
                id=vid,
                slug=str(raw["slug"]),
                form_version=str(raw["form_version"]),
                title=str(raw["title"]),
                original_pdf=raw.get("original_pdf") or b"",
                original_hash=str(raw["original_hash"]),
                page_geometry=raw.get("page_geometry") or [],
                coord_map=cmap,
                coord_map_hash=str(raw.get("coord_map_hash") or cmap.content_hash()),
                allowed_font_name=str(raw.get("allowed_font_name", "")),
                allowed_font_hash=str(raw.get("allowed_font_hash", "")),
                font_license=str(raw.get("font_license", "")),
                field_schema=dict(raw.get("field_schema") or {}),
                valid_from=date.fromisoformat(str(raw["valid_from"])),
                valid_to=date.fromisoformat(str(raw["valid_to"])) if raw.get("valid_to") else None,
                review_status=str(raw.get("review_status", "draft")),
                author_id=str(raw.get("author_id", "")),
                catalog_form_id=UUID(str(raw["catalog_form_id"])) if raw.get("catalog_form_id") else None,
                second_reviewer_id=raw.get("second_reviewer_id"),
                published_at=_parse_dt(raw.get("published_at")),
                source_snapshot_id=UUID(str(raw["source_snapshot_id"])) if raw.get("source_snapshot_id") else None,
                blocked_reason=raw.get("blocked_reason"),
                created_at=_parse_dt(raw.get("created_at")) or datetime.now(),
            )
            service.versions[rec.id] = rec
            service.by_slug_ver[(rec.slug, rec.form_version)] = rec.id

    by_catalog = _load_blob("form_fill", "by_catalog")
    if isinstance(by_catalog, dict):
        service.by_catalog = {UUID(str(k)): UUID(str(v)) for k, v in by_catalog.items()}

    generated_payload = _load_blob("form_fill", "generated")
    if isinstance(generated_payload, dict):
        for key, raw in generated_payload.items():
            if not isinstance(raw, dict):
                continue
            service.generated[UUID(str(key))] = GeneratedFormRecord(
                id=UUID(str(key)),
                user_id=UUID(str(raw["user_id"])),
                form_version_id=UUID(str(raw["form_version_id"])),
                catalog_form_id=UUID(str(raw["catalog_form_id"])) if raw.get("catalog_form_id") else None,
                answers=dict(raw.get("answers") or {}),
                template_hash=str(raw.get("template_hash", "")),
                coord_map_hash=str(raw.get("coord_map_hash", "")),
                input_hash=str(raw.get("input_hash", "")),
                output_hash=str(raw.get("output_hash", "")),
                engine_version=str(raw.get("engine_version", "")),
                output_pdf=raw.get("output_pdf") or b"",
                preview=dict(raw.get("preview") or {}),
                audit=list(raw.get("audit") or []),
                created_at=_parse_dt(raw.get("created_at")) or datetime.now(),
                deleted_at=_parse_dt(raw.get("deleted_at")),
            )

    drafts_payload = _load_blob("form_fill", "drafts")
    if isinstance(drafts_payload, dict):
        for key, raw in drafts_payload.items():
            if not isinstance(raw, dict):
                continue
            service.drafts[UUID(str(key))] = FormDraftRecord(
                id=UUID(str(key)),
                user_id=UUID(str(raw["user_id"])),
                catalog_form_id=UUID(str(raw["catalog_form_id"])),
                form_version_id=UUID(str(raw["form_version_id"])),
                answers=dict(raw.get("answers") or {}),
                updated_at=_parse_dt(raw.get("updated_at")) or datetime.now(),
            )

    coord_payload = _load_blob("form_fill", "coord_drafts")
    if isinstance(coord_payload, dict):
        for key, raw in coord_payload.items():
            if not isinstance(raw, dict):
                continue
            service.coord_drafts[UUID(str(key))] = CoordMapDraft(
                id=UUID(str(key)),
                form_version_id=UUID(str(raw["form_version_id"])),
                author_id=str(raw.get("author_id", "")),
                map_json=str(raw.get("map_json", "")),
                status=str(raw.get("status", "draft")),
                second_reviewer_id=raw.get("second_reviewer_id"),
                created_at=_parse_dt(raw.get("created_at")) or datetime.now(),
            )


def _persist_form_fill_store(service: Any) -> None:
    versions_payload = {str(k): asdict(v) for k, v in service.versions.items()}
    _save_blob("form_fill", "versions", versions_payload)
    _save_blob("form_fill", "by_catalog", {str(k): str(v) for k, v in service.by_catalog.items()})
    _save_blob("form_fill", "generated", {str(k): asdict(v) for k, v in service.generated.items()})
    _save_blob("form_fill", "drafts", {str(k): asdict(v) for k, v in service.drafts.items()})
    _save_blob("form_fill", "coord_drafts", {str(k): asdict(v) for k, v in service.coord_drafts.items()})


def _blob_store_specs(app_state: Any) -> list[tuple[str, Any, list[str]]]:
    specs: list[tuple[str, Any, list[str]]] = []
    mapping = [
        ("sources", "source_registry", ["sources", "snapshots", "norms_status", "forms_status"]),
        ("forms", "form_catalog", ["forms", "raw_store"]),
        ("form_fill", "form_fill", []),
        ("billing", "billing", ["subscriptions", "attempts", "webhooks", "refunds", "idempotency"]),
        ("entry", "entry_wizard", ["drafts", "snapshots"]),
        ("feedback", "feedback_store", ["events"]),
        ("medical", "medical_section", ["procedures", "orgs"]),
    ]
    for ns, attr, keys in mapping:
        store = getattr(app_state, attr, None)
        if store is not None:
            specs.append((ns, store, keys))
    return specs


def mark_analysis_dirty() -> None:
    _flag("analysis").mark()


def mark_auth_dirty() -> None:
    _flag("auth").mark()


def mark_blob_dirty(namespace: str) -> None:
    _flag(namespace).mark()
