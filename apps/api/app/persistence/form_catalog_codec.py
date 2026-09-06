"""Explicit FormRecord codec. Never put a dict into the domain catalog."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from app.persistence.serde import persistence_dumps, persistence_loads
from app.services.forms.catalog import FormRecord, utcnow

CATALOG_USER_MESSAGE = "Не удалось обработать карточку шаблона. Запись изолирована; остальные шаблоны доступны."
CATALOG_FATAL_MESSAGE = "Не удалось загрузить каталог шаблонов. Передайте в поддержку код обращения."
CATALOG_STATUS_VALUES = frozenset({"draft", "needs_review", "published", "superseded"})


class CatalogPersistenceError(Exception):
    def __init__(self, code: str, message: str, correlation_id: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.correlation_id = correlation_id

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "detail": self.message,
            "correlation_id": self.correlation_id,
        }


def new_correlation_id() -> str:
    return uuid4().hex


def catalog_fatal(code: str, *, message: str = CATALOG_FATAL_MESSAGE) -> CatalogPersistenceError:
    return CatalogPersistenceError(code, message, new_correlation_id())


def _as_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def as_bytes(value: Any) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value
    if isinstance(value, dict) and set(value.keys()) == {"__bytes__"}:
        return persistence_loads(persistence_dumps(value))
    if isinstance(value, str):
        restored = persistence_loads(persistence_dumps({"__bytes__": value}))
        return restored if isinstance(restored, bytes) else None
    return None


def form_record_to_payload(rec: FormRecord) -> dict[str, Any]:
    return {
        "id": str(rec.id),
        "slug": rec.slug,
        "title": rec.title,
        "organ": rec.organ,
        "purpose": rec.purpose,
        "region": rec.region,
        "authority": rec.authority,
        "status": rec.status,
        "source_snapshot_id": str(rec.source_snapshot_id) if rec.source_snapshot_id else None,
        "content_sha256": rec.content_sha256,
        "raw_size": rec.raw_size,
        "act_number": rec.act_number,
        "act_date": rec.act_date.isoformat() if rec.act_date else None,
        "act_title": rec.act_title,
        "valid_from": rec.valid_from.isoformat() if rec.valid_from else None,
        "valid_to": rec.valid_to.isoformat() if rec.valid_to else None,
        "reviewed_at": rec.reviewed_at.isoformat() if rec.reviewed_at else None,
        "reviewer": rec.reviewer,
        "warning": rec.warning,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "edition_note": rec.edition_note,
        "category": rec.category,
        "form_kind": rec.form_kind,
        "fill_ready": rec.fill_ready,
        "fill_version_id": str(rec.fill_version_id) if rec.fill_version_id else None,
    }


def form_record_from_mapping(key: Any, payload: Any) -> FormRecord:
    if isinstance(payload, FormRecord):
        rec = payload
    else:
        if not isinstance(payload, dict):
            raise ValueError("catalog_payload_not_object")
        rec_id = _as_uuid(payload.get("id") or key)
        if rec_id is None:
            raise ValueError("catalog_id_missing")
        rec = FormRecord(
            id=rec_id,
            slug=str(payload.get("slug") or ""),
            title=str(payload.get("title") or ""),
            organ=str(payload.get("organ") or ""),
            purpose=str(payload.get("purpose") or ""),
            region=str(payload.get("region") or "RF"),
            authority=str(payload.get("authority") or payload.get("organ") or ""),
            status=str(payload.get("status") or "needs_review"),
            source_snapshot_id=_as_uuid(payload.get("source_snapshot_id")),
            content_sha256=str(payload["content_sha256"]) if payload.get("content_sha256") else None,
            raw_size=int(payload.get("raw_size") or 0),
            act_number=payload.get("act_number"),
            act_date=_as_date(payload.get("act_date")),
            act_title=payload.get("act_title"),
            valid_from=_as_date(payload.get("valid_from")),
            valid_to=_as_date(payload.get("valid_to")),
            reviewed_at=_as_dt(payload.get("reviewed_at")),
            reviewer=payload.get("reviewer"),
            warning=str(payload.get("warning") or ""),
            created_at=_as_dt(payload.get("created_at")) or utcnow(),
            edition_note=str(payload.get("edition_note") or ""),
            category=str(payload.get("category") or "entry_stay"),
            form_kind=str(payload.get("form_kind") or "government_form"),
            fill_ready=bool(payload.get("fill_ready") or False),
            fill_version_id=_as_uuid(payload.get("fill_version_id")),
        )
    if not rec.slug or not rec.title:
        raise ValueError("catalog_required_fields")
    if rec.status not in CATALOG_STATUS_VALUES:
        raise ValueError("catalog_status_invalid")
    return rec
