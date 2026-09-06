"""Form catalog — publish only with approved official source + verified raw hash."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.services.forms.fill.generation_gates import clamp_catalog_fill_ready
from app.services.sources.registry import SourceRegistry, SourceState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FormError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


# Candidate known from secondary refs; MUST NOT be published without official raw verification.
MVP_MVD_CANDIDATE = {
    "slug": "mvd.arrival_notice.app4",
    "title": "Уведомление о прибытии иностранного гражданина (прил. 4 к приказу МВД N 856)",
    "organ": "МВД России",
    "purpose": "migration_registration",
    "region": "RF",
    "candidate_act_number": "856",
    "candidate_act_title": "Приказ МВД России от 10.12.2020 N 856 (ред. от 22.10.2024 N 628)",
    "official_source_hint": "publication.pravo.gov.ru / mvd.gov.ru — требуется утверждённый snapshot с raw",
}


@dataclass
class FormRecord:
    id: UUID
    slug: str
    title: str
    organ: str
    purpose: str
    region: str
    authority: str
    status: str  # draft|needs_review|published|superseded
    source_snapshot_id: UUID | None
    content_sha256: str | None
    raw_size: int
    act_number: str | None
    act_date: date | None
    act_title: str | None
    valid_from: date | None
    valid_to: date | None
    reviewed_at: datetime | None
    reviewer: str | None
    warning: str
    created_at: datetime = field(default_factory=utcnow)
    edition_note: str = ""
    category: str = "entry_stay"
    form_kind: str = "government_form"  # government_form | medical_memo
    fill_ready: bool = False
    fill_version_id: UUID | None = None


@dataclass
class AbuseReport:
    id: UUID
    target_type: str
    target_id: str
    reason: str
    comment: str
    reporter_user_id: UUID | None
    created_at: datetime = field(default_factory=utcnow)


class FormCatalogService:
    def __init__(self, sources: SourceRegistry) -> None:
        self.sources = sources
        self.forms: dict[UUID, FormRecord] = {}
        self.by_slug: dict[str, UUID] = {}
        self.raw_store: dict[UUID, bytes] = {}
        self.abuse_reports: list[AbuseReport] = []
        self.verification_log: list[dict[str, Any]] = []
        self.quarantine: list[dict[str, str]] = []
        self._persist = False

    def enable_persist(self) -> None:
        self._persist = True

    def _persist_record(self, rec: FormRecord, raw: bytes | None = None) -> None:
        if not self._persist:
            return
        from app.persistence.form_catalog_repo import upsert_form

        upsert_form(rec, raw=self.raw_store.get(rec.id) if raw is None else raw)

    def isolate(self, record_key: Any, *, code: str, payload: Any = None) -> dict[str, str]:
        from app.persistence.form_catalog_codec import CATALOG_USER_MESSAGE, new_correlation_id

        item = {
            "record_key": str(record_key),
            "code": code,
            "message": CATALOG_USER_MESSAGE,
            "correlation_id": new_correlation_id(),
        }
        self.quarantine.append(item)
        if self._persist:
            from app.persistence.form_catalog_repo import quarantine

            quarantine(record_key=str(record_key), code=code, payload=payload, correlation_id=item["correlation_id"])
        return item

    def put(self, rec: FormRecord, *, raw: bytes | None = None) -> FormRecord:
        if not isinstance(rec, FormRecord):
            raise TypeError("catalog_requires_form_record")
        if raw is not None:
            self.raw_store[rec.id] = raw
            rec.raw_size = len(raw)
        clamp_catalog_fill_ready(rec)
        self.forms[rec.id] = rec
        self.by_slug[rec.slug] = rec.id
        self._persist_record(rec, raw=raw)
        return rec

    def update_fields(self, form_id: UUID, **fields: Any) -> FormRecord:
        rec = self.get(form_id)
        for name, value in fields.items():
            if not hasattr(rec, name):
                raise AttributeError(name)
            setattr(rec, name, value)
        clamp_catalog_fill_ready(rec)
        if rec.slug:
            self.by_slug[rec.slug] = rec.id
        self._persist_record(rec)
        return rec

    def rebuild_slug_index(self) -> None:
        index: dict[str, UUID] = {}
        for rec in self.iter_records():
            index[rec.slug] = rec.id
        self.by_slug = index

    def iter_records(self) -> list[FormRecord]:
        return [rec for rec in self.forms.values() if isinstance(rec, FormRecord)]

    def typed_catalog_ok(self) -> bool:
        if any(not isinstance(v, FormRecord) for v in self.forms.values()):
            return False
        try:
            self.list_forms()
        except Exception:
            return False
        return True

    def apply_invariants(self, *, fill_version_ids: set[UUID], snapshot_ids: set[UUID]) -> None:
        remapped: dict[UUID, FormRecord] = {}
        drop_keys: list[UUID] = []
        for key, value in list(self.forms.items()):
            if not isinstance(value, FormRecord):
                try:
                    from app.persistence.form_catalog_codec import form_record_from_mapping

                    rec = form_record_from_mapping(key, value)
                except Exception as exc:  # noqa: BLE001
                    self.isolate(key, code="catalog_record_invalid", payload=str(exc))
                    drop_keys.append(key)
                    continue
            else:
                rec = value
            if rec.id != key:
                self.isolate(key, code="catalog_id_mismatch", payload=str(key))
                drop_keys.append(key)
                continue
            if rec.fill_version_id and rec.fill_version_id not in fill_version_ids:
                rec.fill_version_id = None
                rec.fill_ready = False
                self.isolate(rec.id, code="catalog_fill_version_missing", payload=str(rec.id))
            published_needs_snapshot = rec.status == "published" and rec.form_kind == "government_form"
            if published_needs_snapshot:
                if rec.source_snapshot_id is None or rec.source_snapshot_id not in snapshot_ids:
                    rec.status = "needs_review"
                    rec.fill_ready = False
                    rec.fill_version_id = None
                    self.isolate(rec.id, code="catalog_snapshot_missing", payload=str(rec.id))
            clamp_catalog_fill_ready(rec)
            remapped[rec.id] = rec
        for key in drop_keys:
            self.forms.pop(key, None)
        self.forms = remapped
        self.rebuild_slug_index()
        if self._persist:
            for rec in remapped.values():
                self._persist_record(rec)

    def seed_mvp_mvd_verification(self, *, attempt_fetch: bool = True) -> FormRecord:
        """
        Attempt MVP MVD form inclusion. Without approved official raw + clear edition,
        do NOT publish — expose needs_review card only.
        """
        note = {
            "candidate": MVP_MVD_CANDIDATE["slug"],
            "at": utcnow().isoformat(),
            "attempt_fetch": attempt_fetch,
        }
        # Check whether an approved MVD/pravo snapshot with usable raw already exists
        usable = self._find_usable_mvd_snapshot()
        if not usable:
            note["result"] = "needs_review"
            note["reason"] = (
                "Официальный raw-файл формы МВД (прил. 4 к приказу N 856) не верифицирован: "
                "нет approved snapshot с ясным актом/редакцией или файл недоступен. "
                "Форма не добавлена в published-каталог."
            )
            self.verification_log.append(note)
            rec = FormRecord(
                id=uuid4(),
                slug=MVP_MVD_CANDIDATE["slug"],
                title=MVP_MVD_CANDIDATE["title"],
                organ=MVP_MVD_CANDIDATE["organ"],
                purpose=MVP_MVD_CANDIDATE["purpose"],
                region=MVP_MVD_CANDIDATE["region"],
                authority="МВД России",
                status="needs_review",
                source_snapshot_id=None,
                content_sha256=None,
                raw_size=0,
                act_number=MVP_MVD_CANDIDATE["candidate_act_number"],
                act_date=None,
                act_title=MVP_MVD_CANDIDATE["candidate_act_title"],
                valid_from=None,
                valid_to=None,
                reviewed_at=None,
                reviewer=None,
                warning=(
                    "needs_review: официальный оригинал не подтверждён. "
                    "Каталог не выдаёт форму без approved metadata и raw SHA-256."
                ),
                edition_note="Кандидат; публикация заблокирована до editorial verification",
            )
            self.put(rec)
            return rec

        snap_id, snap = usable
        # Even with a snapshot, if act metadata is incomplete → needs_review, do not publish
        if not snap.act_number or not snap.act_date or not snap.valid_from:
            note["result"] = "needs_review"
            note["reason"] = "Редакция/акт на approved snapshot неполны"
            self.verification_log.append(note)
            rec = FormRecord(
                id=uuid4(),
                slug=MVP_MVD_CANDIDATE["slug"],
                title=MVP_MVD_CANDIDATE["title"],
                organ=MVP_MVD_CANDIDATE["organ"],
                purpose=MVP_MVD_CANDIDATE["purpose"],
                region=MVP_MVD_CANDIDATE["region"],
                authority="МВД России",
                status="needs_review",
                source_snapshot_id=snap_id,
                content_sha256=snap.content_hash or None,
                raw_size=len(snap.raw or b""),
                act_number=snap.act_number,
                act_date=snap.act_date,
                act_title=snap.act_title,
                valid_from=snap.valid_from,
                valid_to=snap.valid_to,
                reviewed_at=snap.reviewed_at,
                reviewer=snap.reviewer_id,
                warning="needs_review: редакция акта неясна — форма не опубликована",
            )
            self.put(rec)
            return rec

        # Publish only when raw present and hash known
        raw = snap.raw or b""
        if not raw or not snap.content_hash:
            note["result"] = "needs_review"
            note["reason"] = "Raw original отсутствует"
            self.verification_log.append(note)
            raise FormError("raw_missing", "Cannot publish without raw original")

        note["result"] = "published"
        self.verification_log.append(note)
        return self.register_form(
            slug=MVP_MVD_CANDIDATE["slug"],
            title=MVP_MVD_CANDIDATE["title"],
            organ=MVP_MVD_CANDIDATE["organ"],
            purpose=MVP_MVD_CANDIDATE["purpose"],
            region=MVP_MVD_CANDIDATE["region"],
            authority="МВД России",
            source_snapshot_id=snap_id,
            raw_original=raw,
            content_sha256=snap.content_hash,
            act_number=snap.act_number,
            act_date=snap.act_date,
            act_title=snap.act_title or MVP_MVD_CANDIDATE["candidate_act_title"],
            valid_from=snap.valid_from,
            valid_to=snap.valid_to,
            reviewed_at=snap.reviewed_at or utcnow(),
            reviewer=snap.reviewer_id or "system",
            warning="Информационный шаблон; автоотправка в госсиистемы вне MVP.",
        )

    def _find_usable_mvd_snapshot(self) -> tuple[UUID, Any] | None:
        for src in self.sources.sources.values():
            host = (src.host or "").lower()
            if not any(x in host for x in ("mvd.gov.ru", "pravo.gov.ru", "publication.pravo.gov.ru")):
                continue
            approved = self.sources.approved_snapshot(src.id)
            if approved and approved.state == SourceState.APPROVED and approved.raw:
                return approved.id, approved
        return None

    def register_form(
        self,
        *,
        slug: str,
        title: str,
        organ: str,
        purpose: str,
        region: str,
        authority: str,
        source_snapshot_id: UUID,
        raw_original: bytes,
        content_sha256: str,
        act_number: str,
        act_date: date,
        act_title: str,
        valid_from: date,
        valid_to: date | None,
        reviewed_at: datetime,
        reviewer: str,
        warning: str = "Не является официальной подачей в госорган.",
    ) -> FormRecord:
        if not raw_original:
            raise FormError("raw_required", "Raw original file is required")
        digest = hashlib.sha256(raw_original).hexdigest()
        if digest != content_sha256.lower():
            raise FormError("hash_mismatch", "SHA-256 does not match raw original")

        snap = self.sources.snapshots.get(source_snapshot_id)
        if not snap or snap.state != SourceState.APPROVED:
            raise FormError("source_not_approved", "Form requires approved official source snapshot", http_status=403)
        if not self.sources.applicable_on(source_snapshot_id, date.today()):
            raise FormError("source_not_applicable", "Approved snapshot not applicable on registration date")

        if not act_number or not act_date or not act_title:
            raise FormError("act_metadata_required", "Act number/date/title required")
        if not authority or not purpose or not organ:
            raise FormError("metadata_required", "organ, purpose, authority required")
        if not reviewer or not reviewed_at:
            raise FormError("review_required", "reviewer and review date required")
        if valid_from is None:
            raise FormError("valid_from_required", "valid_from required")

        if slug in self.by_slug:
            raise FormError("slug_exists", "Form slug already registered", http_status=409)

        rec = FormRecord(
            id=uuid4(),
            slug=slug,
            title=title,
            organ=organ,
            purpose=purpose,
            region=region,
            authority=authority,
            status="published",
            source_snapshot_id=source_snapshot_id,
            content_sha256=digest,
            raw_size=len(raw_original),
            act_number=act_number,
            act_date=act_date,
            act_title=act_title,
            valid_from=valid_from,
            valid_to=valid_to,
            reviewed_at=reviewed_at,
            reviewer=reviewer,
            warning=warning,
            edition_note=f"{act_title} №{act_number} от {act_date.isoformat()}",
        )
        self.put(rec, raw=raw_original)
        self.sources.bind_dependent(snap.source_id, form_id=slug)
        return rec

    def list_forms(
        self,
        *,
        organ: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
        region: str | None = None,
        category: str | None = None,
        search: str | None = None,
        as_of: date | None = None,
        include_unpublished: bool = True,
    ) -> list[FormRecord]:
        on = as_of or date.today()
        q = (search or "").strip().lower()
        out: list[FormRecord] = []
        drop_keys: list[UUID] = []
        for key, f in list(self.forms.items()):
            if not isinstance(f, FormRecord):
                self.isolate(key, code="catalog_record_invalid", payload=type(f).__name__)
                drop_keys.append(key)
                continue
            if organ and f.organ.lower() != organ.lower():
                continue
            if purpose and f.purpose != purpose:
                continue
            if category and f.category != category:
                continue
            if q and q not in f.title.lower() and q not in f.slug.lower() and q not in f.organ.lower():
                continue
            if status and f.status != status:
                continue
            if region and f.region.upper() != region.upper() and f.region != "RF":
                continue
            if f.status == "published":
                if f.valid_from and on < f.valid_from:
                    continue
                if f.valid_to and on > f.valid_to:
                    continue
            elif not include_unpublished:
                continue
            out.append(f)
        for key in drop_keys:
            self.forms.pop(key, None)
        return sorted(out, key=lambda x: x.title)

    def get(self, form_id: UUID) -> FormRecord:
        rec = self.forms.get(form_id)
        if rec is None:
            raise FormError("not_found", "Form not found", http_status=404)
        if not isinstance(rec, FormRecord):
            self.isolate(form_id, code="catalog_record_invalid", payload=type(rec).__name__)
            self.forms.pop(form_id, None)
            raise FormError("not_found", "Form not found", http_status=404)
        return rec

    def unavailable_reason(self, f: FormRecord) -> str | None:
        if f.status == "superseded":
            return "Редакция снята с публикации. Новые документы по этой версии недоступны."
        if f.form_kind == "medical_memo":
            if f.status == "published" and f.fill_ready and f.fill_version_id:
                return None
            return "Собственная памятка сервиса ещё не открыта для заполнения."
        if not f.fill_ready or not f.fill_version_id or f.status != "published":
            return f.warning or (
                "Заполнение откроется после проверки официального бланка, источника и карты полей двумя редакторами."
            )
        return None

    def card(self, f: FormRecord) -> dict[str, Any]:
        from app.services.forms.official_form_acts import act_for_slug

        src_payload = None
        if f.source_snapshot_id:
            try:
                src_payload = self.sources.citation(f.source_snapshot_id, quote=f.title, on_date=date.today())
            except Exception:
                src_payload = None
        act = act_for_slug(f.slug)
        official_url = None
        if isinstance(src_payload, dict) and src_payload.get("official_url"):
            official_url = src_payload.get("official_url")
        elif act:
            official_url = act.get("official_url")
        return {
            "id": str(f.id),
            "slug": f.slug,
            "title": f.title,
            "organ": f.organ,
            "purpose": f.purpose,
            "region": f.region,
            "authority": f.authority,
            "status": f.status,
            "edition": f.edition_note,
            "act_number": f.act_number,
            "act_date": f.act_date.isoformat() if f.act_date else None,
            "act_title": f.act_title,
            "valid_from": f.valid_from.isoformat() if f.valid_from else None,
            "valid_to": f.valid_to.isoformat() if f.valid_to else None,
            "reviewed_at": f.reviewed_at.isoformat() if f.reviewed_at else None,
            "reviewer": f.reviewer,
            "content_sha256": f.content_sha256,
            "source": src_payload,
            "official_url": official_url,
            "appendix": (act or {}).get("appendix"),
            "unified_official_form": (act or {}).get("unified_form"),
            "warning": f.warning,
            "has_raw": f.id in self.raw_store and f.raw_size > 0,
            "category": f.category,
            "category_label": {
                "entry_stay": "Въезд и пребывание",
                "work": "Работа",
                "rvp_vnz": "РВП и ВНЖ",
                "medical": "Медицинские памятки",
            }.get(f.category, f.category),
            "form_kind": f.form_kind,
            "fill_ready": f.fill_ready,
            "worksheet_ready": f.form_kind == "government_form",
            "fill_version_id": str(f.fill_version_id) if f.fill_version_id else None,
            "unavailable_reason": self.unavailable_reason(f),
        }

    def report_abuse(
        self,
        *,
        target_type: str,
        target_id: str,
        reason: str,
        comment: str = "",
        reporter_user_id: UUID | None = None,
    ) -> AbuseReport:
        allowed_types = {"form", "source", "medical_org", "medical_procedure"}
        allowed_reasons = {"outdated", "incorrect", "abuse", "other"}
        if target_type not in allowed_types:
            raise FormError("invalid_target", "Invalid abuse target type")
        if reason not in allowed_reasons:
            raise FormError("invalid_reason", "Invalid abuse reason")
        rep = AbuseReport(
            id=uuid4(),
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            comment=comment[:2000],
            reporter_user_id=reporter_user_id,
        )
        self.abuse_reports.append(rep)
        return rep
