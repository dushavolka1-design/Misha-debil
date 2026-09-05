"""SQL repository for fill versions, drafts and generated PDFs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models import FillRuntimeDraft, FillRuntimeGenerated, FillRuntimeVersion
from app.persistence.sync_db import get_sync_engine, sync_session
from app.services.forms.fill.coord_map import CoordinateMap
from app.services.forms.fill.service import FormDraftRecord, FormVersionRecord, GeneratedFormRecord


def fill_runtime_tables_ready() -> bool:
    try:
        insp = inspect(get_sync_engine())
        return insp.has_table("fill_runtime_versions")
    except Exception:
        return False


def _write_version(sess: Session, rec: FormVersionRecord) -> None:
    row = sess.get(FillRuntimeVersion, rec.id)
    if row is None:
        row = FillRuntimeVersion(id=rec.id)
        sess.add(row)
    row.slug = rec.slug
    row.form_version = rec.form_version
    row.title = rec.title
    row.original_pdf = rec.original_pdf
    row.original_hash = rec.original_hash
    row.page_geometry_json = rec.page_geometry
    row.coord_map_json = rec.coord_map.to_json()
    row.coord_map_hash = rec.coord_map_hash
    row.allowed_font_name = rec.allowed_font_name
    row.allowed_font_hash = rec.allowed_font_hash
    row.font_license = rec.font_license
    row.field_schema_json = rec.field_schema
    row.valid_from = rec.valid_from
    row.valid_to = rec.valid_to
    row.review_status = rec.review_status
    row.author_id = rec.author_id
    row.catalog_form_id = rec.catalog_form_id
    row.second_reviewer_id = rec.second_reviewer_id
    row.published_at = rec.published_at
    row.source_snapshot_id = rec.source_snapshot_id
    row.blocked_reason = rec.blocked_reason
    row.created_at = rec.created_at


def upsert_version(rec: FormVersionRecord) -> None:
    with sync_session() as sess:
        _write_version(sess, rec)
        sess.commit()


def _write_draft(sess: Session, rec: FormDraftRecord) -> None:
    row = sess.get(FillRuntimeDraft, rec.id)
    if row is None:
        row = FillRuntimeDraft(id=rec.id)
        sess.add(row)
    row.user_id = rec.user_id
    row.catalog_form_id = rec.catalog_form_id
    row.form_version_id = rec.form_version_id
    row.answers_json = rec.answers
    row.updated_at = rec.updated_at


def upsert_draft(rec: FormDraftRecord) -> None:
    with sync_session() as sess:
        _write_draft(sess, rec)
        sess.commit()


def _write_generated(sess: Session, rec: GeneratedFormRecord) -> None:
    row = sess.get(FillRuntimeGenerated, rec.id)
    if row is None:
        row = FillRuntimeGenerated(id=rec.id)
        sess.add(row)
    row.user_id = rec.user_id
    row.form_version_id = rec.form_version_id
    row.catalog_form_id = rec.catalog_form_id
    row.answers_json = rec.answers
    row.template_hash = rec.template_hash
    row.coord_map_hash = rec.coord_map_hash
    row.input_hash = rec.input_hash
    row.output_hash = rec.output_hash
    row.engine_version = rec.engine_version
    row.output_pdf = rec.output_pdf
    row.preview_json = rec.preview
    row.audit_json = rec.audit
    row.created_at = rec.created_at
    row.deleted_at = rec.deleted_at


def upsert_generated(rec: GeneratedFormRecord) -> None:
    with sync_session() as sess:
        _write_generated(sess, rec)
        sess.commit()


def _row_to_version(row: FillRuntimeVersion) -> FormVersionRecord:
    cmap = CoordinateMap.from_json(row.coord_map_json)
    return FormVersionRecord(
        id=row.id,
        slug=row.slug,
        form_version=row.form_version,
        title=row.title,
        original_pdf=row.original_pdf or b"",
        original_hash=row.original_hash,
        page_geometry=list(row.page_geometry_json or []),
        coord_map=cmap,
        coord_map_hash=row.coord_map_hash,
        allowed_font_name=row.allowed_font_name,
        allowed_font_hash=row.allowed_font_hash,
        font_license=row.font_license or "",
        field_schema=dict(row.field_schema_json or {}),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        review_status=row.review_status,
        author_id=row.author_id,
        catalog_form_id=row.catalog_form_id,
        second_reviewer_id=row.second_reviewer_id,
        published_at=row.published_at,
        source_snapshot_id=row.source_snapshot_id,
        blocked_reason=row.blocked_reason,
        created_at=row.created_at or datetime.now(timezone.utc),
    )


def load_fill_runtime() -> tuple[
    dict[UUID, FormVersionRecord],
    dict[UUID, UUID],
    dict[UUID, FormDraftRecord],
    dict[UUID, GeneratedFormRecord],
]:
    versions: dict[UUID, FormVersionRecord] = {}
    by_catalog: dict[UUID, UUID] = {}
    drafts: dict[UUID, FormDraftRecord] = {}
    generated: dict[UUID, GeneratedFormRecord] = {}
    if not fill_runtime_tables_ready():
        return versions, by_catalog, drafts, generated
    with sync_session() as sess:
        for row in sess.scalars(select(FillRuntimeVersion)).all():
            rec = _row_to_version(row)
            versions[rec.id] = rec
            if rec.catalog_form_id:
                by_catalog[rec.catalog_form_id] = rec.id
        for row in sess.scalars(select(FillRuntimeDraft)).all():
            drafts[row.id] = FormDraftRecord(
                id=row.id,
                user_id=row.user_id,
                catalog_form_id=row.catalog_form_id,
                form_version_id=row.form_version_id,
                answers=dict(row.answers_json or {}),
                updated_at=row.updated_at or datetime.now(timezone.utc),
            )
        for row in sess.scalars(select(FillRuntimeGenerated)).all():
            generated[row.id] = GeneratedFormRecord(
                id=row.id,
                user_id=row.user_id,
                form_version_id=row.form_version_id,
                catalog_form_id=row.catalog_form_id,
                answers=dict(row.answers_json or {}),
                template_hash=row.template_hash,
                coord_map_hash=row.coord_map_hash,
                input_hash=row.input_hash,
                output_hash=row.output_hash,
                engine_version=row.engine_version,
                output_pdf=row.output_pdf or b"",
                preview=dict(row.preview_json or {}),
                audit=list(row.audit_json or []),
                created_at=row.created_at or datetime.now(timezone.utc),
                deleted_at=row.deleted_at,
            )
    return versions, by_catalog, drafts, generated
