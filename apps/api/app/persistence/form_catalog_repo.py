"""Transactional form catalog repository. Not a single JSON blob for the whole catalog."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models import CatalogBlobBackup, CatalogForm, CatalogQuarantine
from app.persistence.form_catalog_codec import (
    CATALOG_USER_MESSAGE,
    CatalogPersistenceError,
    as_bytes,
    catalog_fatal,
    form_record_from_mapping,
    new_correlation_id,
)
from app.persistence.sync_db import get_sync_engine, sync_session
from app.services.forms.catalog import FormRecord


def catalog_tables_ready() -> bool:
    try:
        return inspect(get_sync_engine()).has_table("catalog_forms")
    except Exception:
        return False


def _write_row(sess: Session, rec: FormRecord, raw: bytes | None) -> None:
    row = sess.get(CatalogForm, rec.id)
    if row is None:
        row = CatalogForm(id=rec.id)
        sess.add(row)
    row.slug = rec.slug
    row.title = rec.title
    row.organ = rec.organ
    row.purpose = rec.purpose
    row.region = rec.region
    row.authority = rec.authority
    row.status = rec.status
    row.source_snapshot_id = rec.source_snapshot_id
    row.content_sha256 = rec.content_sha256
    row.raw_size = rec.raw_size
    row.act_number = rec.act_number
    row.act_date = rec.act_date
    row.act_title = rec.act_title
    row.valid_from = rec.valid_from
    row.valid_to = rec.valid_to
    row.reviewed_at = rec.reviewed_at
    row.reviewer = rec.reviewer
    row.warning = rec.warning
    row.edition_note = rec.edition_note
    row.category = rec.category
    row.form_kind = rec.form_kind
    row.fill_ready = rec.fill_ready
    row.fill_version_id = rec.fill_version_id
    row.created_at = rec.created_at
    if raw is not None:
        row.raw_bytes = raw
        row.raw_size = len(raw)


def upsert_form(rec: FormRecord, *, raw: bytes | None = None, session: Session | None = None) -> None:
    if session is not None:
        _write_row(session, rec, raw)
        return
    with sync_session() as sess:
        try:
            _write_row(sess, rec, raw)
            sess.commit()
        except Exception:
            sess.rollback()
            raise


def row_to_record(row: CatalogForm) -> FormRecord:
    return FormRecord(
        id=row.id,
        slug=row.slug,
        title=row.title,
        organ=row.organ,
        purpose=row.purpose,
        region=row.region,
        authority=row.authority,
        status=row.status,
        source_snapshot_id=row.source_snapshot_id,
        content_sha256=row.content_sha256,
        raw_size=row.raw_size or 0,
        act_number=row.act_number,
        act_date=row.act_date,
        act_title=row.act_title,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        reviewed_at=row.reviewed_at,
        reviewer=row.reviewer,
        warning=row.warning or "",
        created_at=row.created_at,
        edition_note=row.edition_note or "",
        category=row.category,
        form_kind=row.form_kind,
        fill_ready=bool(row.fill_ready),
        fill_version_id=row.fill_version_id,
    )


def _quarantine_item(record_key: str, code: str, correlation_id: str | None = None) -> dict[str, str]:
    return {
        "record_key": str(record_key),
        "code": code,
        "message": CATALOG_USER_MESSAGE,
        "correlation_id": correlation_id or new_correlation_id(),
    }


def add_quarantine(
    sess: Session,
    *,
    record_key: str,
    code: str,
    payload: Any = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    existing = sess.scalars(
        select(CatalogQuarantine).where(CatalogQuarantine.record_key == str(record_key)[:128])
    ).first()
    if existing:
        return {
            "record_key": existing.record_key,
            "code": existing.code,
            "message": existing.message,
            "correlation_id": existing.correlation_id,
        }
    item = _quarantine_item(record_key, code, correlation_id)
    sess.add(
        CatalogQuarantine(
            record_key=str(record_key)[:128],
            code=code,
            message=item["message"],
            correlation_id=item["correlation_id"],
            payload_json={"preview": str(payload)[:2000]} if payload is not None else {},
        )
    )
    return item


def quarantine(
    *,
    record_key: str,
    code: str,
    payload: Any = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    with sync_session() as sess:
        item = add_quarantine(
            sess,
            record_key=record_key,
            code=code,
            payload=payload,
            correlation_id=correlation_id,
        )
        sess.commit()
        return item


def list_quarantine() -> list[dict[str, str]]:
    if not catalog_tables_ready():
        return []
    with sync_session() as sess:
        rows = sess.scalars(select(CatalogQuarantine).order_by(CatalogQuarantine.created_at.desc()).limit(50)).all()
        return [
            {
                "record_key": r.record_key,
                "code": r.code,
                "message": r.message,
                "correlation_id": r.correlation_id,
            }
            for r in rows
        ]


def load_forms() -> tuple[dict[UUID, FormRecord], dict[UUID, bytes], list[dict[str, str]]]:
    if not catalog_tables_ready():
        raise catalog_fatal("catalog_schema_missing")
    forms: dict[UUID, FormRecord] = {}
    raw_store: dict[UUID, bytes] = {}
    isolated: list[dict[str, str]] = []
    try:
        with sync_session() as sess:
            rows = sess.scalars(select(CatalogForm)).all()
            for row in rows:
                try:
                    rec = form_record_from_mapping(row.id, row_to_record(row))
                    if rec.id != row.id:
                        raise ValueError("catalog_id_mismatch")
                    forms[rec.id] = rec
                    if row.raw_bytes:
                        raw_store[rec.id] = row.raw_bytes
                except Exception as exc:  # noqa: BLE001
                    isolated.append(
                        add_quarantine(
                            sess,
                            record_key=str(row.id),
                            code="catalog_record_invalid",
                            payload=str(exc),
                        )
                    )
            sess.commit()
    except CatalogPersistenceError:
        raise
    except Exception as exc:
        raise catalog_fatal("catalog_load_failed") from exc
    return forms, raw_store, isolated


def backup_blob(namespace: str, blob_key: str, value: Any) -> None:
    with sync_session() as sess:
        sess.add(
            CatalogBlobBackup(
                namespace=namespace,
                blob_key=blob_key,
                value_json=value if isinstance(value, dict) else {"value": value},
            )
        )
        sess.commit()


def convert_blob_forms(payload: Any, raw_payload: Any = None) -> tuple[int, list[dict[str, str]]]:
    """Validate and convert a legacy app_state_blobs forms dict. Rollback the transaction on hard failure."""
    if not isinstance(payload, dict):
        raise CatalogPersistenceError("forms_blob_not_object", CATALOG_USER_MESSAGE, new_correlation_id())
    raw_map: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    converted = 0
    isolated: list[dict[str, str]] = []
    with sync_session() as sess:
        try:
            for key, value in payload.items():
                try:
                    rec = form_record_from_mapping(key, value)
                    raw = raw_map.get(str(rec.id)) or raw_map.get(str(key))
                    raw_bytes = as_bytes(raw) if raw is not None else None
                    _write_row(sess, rec, raw_bytes)
                    converted += 1
                except Exception as exc:  # noqa: BLE001
                    isolated.append(
                        add_quarantine(
                            sess,
                            record_key=str(key),
                            code="catalog_record_invalid",
                            payload=str(exc),
                        )
                    )
            sess.commit()
        except Exception:
            sess.rollback()
            raise
    return converted, isolated
