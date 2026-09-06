"""Form fill service: immutable FormVersion, four-eyes publish, GeneratedForm audit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.services.forms.fill.coord_map import (
    BBox,
    CoordField,
    CoordinateMap,
    OverflowStrategy,
    ReservedFor,
    ValueSource,
)
from app.services.forms.fill.engine import ENGINE_VERSION, FillError, FillResult, fill_pdf
from app.services.forms.fill.fonts import font_hash, resolve_allowed_font
from app.services.forms.fill.generation_gates import (
    assert_font_ready,
    assert_government_generatable,
    catalog_checklist,
    download_stem,
    inferred_form_kind,
    is_test_synthetic_slug,
)
from app.services.forms.fill.underlay import UnderlayBuild, build_demo_a4_underlay, build_medical_memo_underlay
from app.services.forms.fill.validate import PreviewResult, validate_inputs
from app.services.sources.registry import SourceRegistry, SourceState


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class FormVersionRecord:
    id: UUID
    slug: str
    form_version: str
    title: str
    original_pdf: bytes
    original_hash: str
    page_geometry: list[list[float]]
    coord_map: CoordinateMap
    coord_map_hash: str
    allowed_font_name: str
    allowed_font_hash: str
    font_license: str
    field_schema: dict[str, Any]
    valid_from: date
    valid_to: date | None
    review_status: str  # draft|awaiting_second_review|published|rejected|blocked_for_new
    author_id: str
    catalog_form_id: UUID | None = None
    second_reviewer_id: str | None = None
    published_at: datetime | None = None
    source_snapshot_id: UUID | None = None
    blocked_reason: str | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class FormDraftRecord:
    id: UUID
    user_id: UUID
    catalog_form_id: UUID
    form_version_id: UUID
    answers: dict[str, str]
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class GeneratedFormRecord:
    id: UUID
    user_id: UUID
    form_version_id: UUID
    catalog_form_id: UUID | None
    answers: dict[str, str]
    template_hash: str
    coord_map_hash: str
    input_hash: str
    output_hash: str
    engine_version: str
    output_pdf: bytes
    preview: dict[str, Any]
    audit: list[dict[str, Any]]
    created_at: datetime = field(default_factory=utcnow)
    deleted_at: datetime | None = None


@dataclass
class CoordMapDraft:
    id: UUID
    form_version_id: UUID
    author_id: str
    map_json: str
    status: str  # draft|awaiting_second_review|approved|rejected
    second_reviewer_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)


class FormFillService:
    def __init__(self, sources: SourceRegistry | None = None, catalog: Any | None = None) -> None:
        self.sources = sources
        self.catalog = catalog
        self.versions: dict[UUID, FormVersionRecord] = {}
        self.by_slug_ver: dict[tuple[str, str], UUID] = {}
        self.by_catalog: dict[UUID, UUID] = {}
        self.generated: dict[UUID, GeneratedFormRecord] = {}
        self.drafts: dict[UUID, FormDraftRecord] = {}
        self.coord_drafts: dict[UUID, CoordMapDraft] = {}
        self._durable = False

    def enable_durable(self) -> None:
        self._durable = True

    def _persist_version(self, rec: FormVersionRecord) -> None:
        if not self._durable:
            return
        from app.persistence.fill_runtime_repo import upsert_version

        upsert_version(rec)

    def _persist_draft(self, rec: FormDraftRecord) -> None:
        if not self._durable:
            return
        from app.persistence.fill_runtime_repo import upsert_draft

        upsert_draft(rec)

    def _persist_generated(self, rec: GeneratedFormRecord) -> None:
        if not self._durable:
            return
        from app.persistence.fill_runtime_repo import upsert_generated

        upsert_generated(rec)

    _ARRIVAL_FIELD_SCHEMA: dict[str, Any] = {
        "full_name": {
            "label": "ФИО иностранного гражданина",
            "hint": "Как в документе, удостоверяющем личность. Кириллица или латиница.",
            "section": "applicant",
            "section_label": "Сведения о прибывшем",
            "required": True,
            "user_editable": True,
        },
        "doc_date": {
            "label": "Дата прибытия / составления",
            "hint": "Формат ДД.ММ.ГГГГ или YYYY-MM-DD.",
            "section": "applicant",
            "section_label": "Сведения о прибывшем",
            "required": True,
            "user_editable": True,
        },
        "notes": {
            "label": "Дополнительные сведения",
            "hint": "Адрес пребывания, цель визита — по необходимости.",
            "section": "stay",
            "section_label": "Пребывание",
            "required": False,
            "user_editable": True,
        },
        "signature": {
            "label": "Подпись заявителя",
            "hint": "Заполняется вручную после печати. Сервис не ставит подпись.",
            "section": "manual",
            "section_label": "Вручную после печати",
            "required": False,
            "user_editable": False,
            "manual_only": True,
        },
        "stamp": {
            "label": "Печать принимающей стороны / органа",
            "hint": "Печать ставит орган. Не генерируется.",
            "section": "manual",
            "section_label": "Вручную после печати",
            "required": False,
            "user_editable": False,
            "manual_only": True,
        },
        "organ_mark": {
            "label": "Отметка органа МВД",
            "hint": "Регистрационный номер и отметка — только сотрудником органа.",
            "section": "organ",
            "section_label": "Только орган",
            "required": False,
            "user_editable": False,
            "manual_only": True,
        },
    }

    _SECTION_ORDER = (
        "head",
        "employer",
        "worker",
        "permit",
        "sign",
        "authority",
        "applicant",
        "person",
        "stay",
        "host",
        "work",
        "invitation",
        "extension",
        "manual",
        "organ",
        "visit",
        "notes",
    )

    _MEDICAL_FIELD_SCHEMA: dict[str, Any] = {
        "visit_date": {
            "label": "Дата визита",
            "hint": "Формат ДД.ММ.ГГГГ или YYYY-MM-DD.",
            "section": "visit",
            "section_label": "Визит",
            "required": True,
            "user_editable": True,
        },
        "questions": {
            "label": "Вопросы врачу",
            "hint": "Свои формулировки. Не указывайте диагноз и не прикладывайте заключение.",
            "section": "visit",
            "section_label": "Визит",
            "required": False,
            "user_editable": True,
            "multiline": True,
        },
        "notes": {
            "label": "Дополнительные заметки",
            "hint": "Только ваши заметки к визиту.",
            "section": "notes",
            "section_label": "Заметки",
            "required": False,
            "user_editable": True,
            "multiline": True,
        },
    }

    def seed_demo_published(self) -> FormVersionRecord:
        """Test-only synthetic FormVersion. Slug must stay under test.synthetic.*."""
        under = build_demo_a4_underlay()
        cmap = self._demo_coord_map(under)
        font_path = resolve_allowed_font()
        rec = FormVersionRecord(
            id=uuid4(),
            slug="test.synthetic.a4",
            form_version="1.0.0",
            title="Test synthetic A4 underlay",
            original_pdf=under.pdf_bytes,
            original_hash=under.content_hash,
            page_geometry=under.page_boxes,
            coord_map=cmap,
            coord_map_hash=cmap.content_hash(),
            allowed_font_name=font_path.name,
            allowed_font_hash=font_hash(font_path),
            font_license="OFL-1.1 Noto Sans — see fill/assets/LICENSE",
            field_schema={
                f.field_id: {
                    "formatter": f.formatter,
                    "required": f.required,
                    "label": f.field_id,
                    "user_editable": f.user_editable,
                }
                for f in cmap.fields
            },
            valid_from=date(2024, 1, 1),
            valid_to=None,
            review_status="published",
            author_id="author@demo",
            second_reviewer_id="reviewer@demo",
            published_at=utcnow(),
        )
        self.versions[rec.id] = rec
        self.by_slug_ver[(rec.slug, rec.form_version)] = rec.id
        self._persist_version(rec)
        return rec

    def seed_medical_memo_published(self, *, catalog_form_id: UUID) -> FormVersionRecord:
        """Own service memo template — not a government form and not an official medical blank."""
        if catalog_form_id in self.by_catalog:
            existing = self.versions[self.by_catalog[catalog_form_id]]
            if existing.slug.startswith("medical."):
                return existing
        under = build_medical_memo_underlay()
        cmap = self._medical_coord_map(under)
        font_path = resolve_allowed_font()
        rec = FormVersionRecord(
            id=uuid4(),
            slug="medical.visit.memo",
            form_version="1.0.0",
            title="Памятка перед визитом к врачу",
            original_pdf=under.pdf_bytes,
            original_hash=under.content_hash,
            page_geometry=under.page_boxes,
            coord_map=cmap,
            coord_map_hash=cmap.content_hash(),
            allowed_font_name=font_path.name,
            allowed_font_hash=font_hash(font_path),
            font_license="OFL-1.1 Noto Sans — see fill/assets/LICENSE",
            field_schema=dict(self._MEDICAL_FIELD_SCHEMA),
            valid_from=date(2024, 1, 1),
            valid_to=None,
            review_status="published",
            author_id="editor@service",
            second_reviewer_id="reviewer@service",
            published_at=utcnow(),
            catalog_form_id=catalog_form_id,
        )
        self.versions[rec.id] = rec
        self.by_slug_ver[(rec.slug, rec.form_version)] = rec.id
        self.by_catalog[catalog_form_id] = rec.id
        self._persist_version(rec)
        return rec

    def seed_worksheet_for_catalog(self, *, catalog_form_id: UUID, slug: str, title: str) -> FormVersionRecord:
        """Service data worksheet — not an official government blank."""
        from app.services.forms.fill.worksheets import WORKSHEET_FORM_VERSION, build_worksheet_pack

        existing_id = self.by_catalog.get(catalog_form_id)
        under, cmap, schema = build_worksheet_pack(slug, title)
        if existing_id:
            existing = self.versions.get(existing_id)
            if (
                existing
                and existing.slug.startswith("worksheet.")
                and existing.form_version == WORKSHEET_FORM_VERSION
                and existing.original_hash == under.content_hash
            ):
                return existing
        font_path = resolve_allowed_font()
        rec = FormVersionRecord(
            id=existing_id
            if existing_id
            and self.versions.get(existing_id)
            and self.versions[existing_id].slug.startswith("worksheet.")
            else uuid4(),
            slug=f"worksheet.{slug}",
            form_version=WORKSHEET_FORM_VERSION,
            title=title,
            original_pdf=under.pdf_bytes,
            original_hash=under.content_hash,
            page_geometry=under.page_boxes,
            coord_map=cmap,
            coord_map_hash=cmap.content_hash(),
            allowed_font_name=font_path.name,
            allowed_font_hash=font_hash(font_path),
            font_license="OFL-1.1 Noto Sans — see fill/assets/LICENSE",
            field_schema=schema,
            valid_from=date(2024, 1, 1),
            valid_to=None,
            review_status="published",
            author_id="editor@service",
            second_reviewer_id="reviewer@service",
            published_at=utcnow(),
            catalog_form_id=catalog_form_id,
        )
        self.versions[rec.id] = rec
        self.by_slug_ver[(rec.slug, rec.form_version)] = rec.id
        self.by_catalog[catalog_form_id] = rec.id
        self._persist_version(rec)
        return rec

    def seed_government_worksheets(self, catalog: Any) -> int:
        seeded = 0
        for rec in catalog.iter_records():
            if rec.form_kind != "government_form":
                continue
            self.seed_worksheet_for_catalog(catalog_form_id=rec.id, slug=rec.slug, title=rec.title)
            seeded += 1
        return seeded

    def get_for_catalog(self, catalog_form_id: UUID) -> FormVersionRecord | None:
        vid = self.by_catalog.get(catalog_form_id)
        if not vid:
            return None
        return self.versions.get(vid)

    def fill_package(self, *, catalog_form_id: UUID, catalog_card: dict[str, Any]) -> dict[str, Any]:
        ver = self.get_for_catalog(catalog_form_id)
        unavailable = catalog_card.get("unavailable_reason")
        kind = catalog_card.get("form_kind") or inferred_form_kind(str(catalog_card.get("slug") or ""))
        checklist = catalog_checklist(catalog_card, version=ver)
        blocked = bool(unavailable) or not ver or not catalog_card.get("fill_ready")
        if blocked or (ver and is_test_synthetic_slug(ver.slug)):
            hint = (
                "Заполните сведения и сверьте их с документами. Условия использования — в пользовательском соглашении."
            )
            if kind == "medical_memo":
                hint = "Памятка сервиса станет доступна после публикации собственного шаблона."
            payload: dict[str, Any] = {
                "catalog_form_id": str(catalog_form_id),
                "available": False,
                "unavailable_reason": unavailable
                or "Заполнение официального бланка откроется после проверки источника и карты полей.",
                "checklist_hint": hint,
                "checklist": checklist,
                "catalog": catalog_card,
            }
            if ver and inferred_form_kind(ver.slug) == "service_worksheet":
                payload["worksheet"] = {
                    "available": True,
                    "mode": "worksheet",
                    "version": self.version_card(ver),
                    "field_schema": ver.field_schema,
                    "sections": self._schema_sections(ver),
                    "underlay_url": f"/forms/fill/versions/{ver.id}/underlay",
                    "preview_title": "Макет сведений",
                }
            return payload
        return {
            "catalog_form_id": str(catalog_form_id),
            "available": True,
            "catalog": catalog_card,
            "version": self.version_card(ver),
            "field_schema": ver.field_schema,
            "sections": self._schema_sections(ver),
            "underlay_url": f"/forms/fill/versions/{ver.id}/underlay",
            "preview_title": "Макет памятки сервиса" if kind == "medical_memo" else "Макет формы",
            "checklist": checklist,
        }

    def _schema_sections(self, ver: FormVersionRecord) -> list[dict[str, Any]]:
        by_section: dict[str, dict[str, Any]] = {}
        for field_id, meta in ver.field_schema.items():
            sec = str(meta.get("section", "default"))
            if sec not in by_section:
                by_section[sec] = {
                    "id": sec,
                    "label": meta.get("section_label") or sec,
                    "fields": [],
                }
            by_section[sec]["fields"].append({"field_id": field_id, **meta})
        ordered = [by_section[s] for s in self._SECTION_ORDER if s in by_section]
        for s, block in by_section.items():
            if s not in self._SECTION_ORDER:
                ordered.append(block)
        return ordered

    def save_draft(
        self,
        *,
        user_id: UUID,
        catalog_form_id: UUID,
        answers: dict[str, str],
    ) -> FormDraftRecord:
        ver = self.get_for_catalog(catalog_form_id)
        if not ver:
            raise FillError("not_available", "Шаблон недоступен для черновика", http_status=409)
        self._require_generatable(ver.id)
        existing = next(
            (d for d in self.drafts.values() if d.user_id == user_id and d.catalog_form_id == catalog_form_id),
            None,
        )
        if existing:
            existing.answers = dict(answers)
            existing.form_version_id = ver.id
            existing.updated_at = utcnow()
            self._persist_draft(existing)
            return existing
        rec = FormDraftRecord(
            id=uuid4(),
            user_id=user_id,
            catalog_form_id=catalog_form_id,
            form_version_id=ver.id,
            answers=dict(answers),
        )
        self.drafts[rec.id] = rec
        self._persist_draft(rec)
        return rec

    def get_draft(self, *, user_id: UUID, catalog_form_id: UUID) -> FormDraftRecord | None:
        return next(
            (d for d in self.drafts.values() if d.user_id == user_id and d.catalog_form_id == catalog_form_id),
            None,
        )

    def list_drafts(self, *, user_id: UUID) -> list[FormDraftRecord]:
        return sorted(
            [d for d in self.drafts.values() if d.user_id == user_id],
            key=lambda d: d.updated_at,
            reverse=True,
        )

    def list_generated_for_user(self, *, user_id: UUID) -> list[GeneratedFormRecord]:
        return sorted(
            [g for g in self.generated.values() if g.user_id == user_id and not g.deleted_at],
            key=lambda g: g.created_at,
            reverse=True,
        )

    def copy_generated(self, generated_id: UUID, *, user_id: UUID) -> GeneratedFormRecord:
        src = self.get_generated(generated_id, user_id=user_id)
        ver = self.versions.get(src.form_version_id)
        if not ver:
            raise FillError("not_found", "FormVersion not found", http_status=404)
        return self.generate(form_version_id=ver.id, user_id=user_id, answers=dict(src.answers))

    def pre_download_checklist(self, form_version_id: UUID, answers: dict[str, str]) -> dict[str, Any]:
        ver = self.versions.get(form_version_id)
        if not ver:
            raise FillError("not_found", "FormVersion not found", http_status=404)
        preview = validate_inputs(ver.coord_map, answers, form_slug=ver.slug, field_schema=ver.field_schema)
        missing_required: list[str] = []
        for field_id, meta in ver.field_schema.items():
            if not meta.get("required"):
                continue
            if not str(answers.get(field_id, "")).strip():
                missing_required.append(str(meta.get("label") or field_id))
        return {
            "title": ver.title,
            "edition": ver.form_version,
            "checked_at": utcnow().isoformat(),
            "preview_ok": preview.ok,
            "missing_required": missing_required,
            "preview_issues": [i.__dict__ for i in preview.issues],
            "manual_review_warning": (
                "Проверьте каждое поле по документам перед подачей. "
                "Статус файла и ограничения сервиса указаны в пользовательском соглашении."
            ),
            "can_download": preview.ok and not missing_required,
        }

    def _demo_coord_map(self, under: UnderlayBuild) -> CoordinateMap:
        # Coordinates match underlay.py layout (A4, origin bottom-left)
        h = under.page_boxes[0][3]
        fields = [
            CoordField(
                field_id="full_name",
                page=0,
                bbox=BBox(50, h - 125, 400, h - 100),
                baseline=h - 118,
                font="FormFillAllowed",
                size=11,
                max_chars=40,
                max_lines=1,
                alphabet="cyrillic_latin_digits",
                overflow_strategy=OverflowStrategy.REJECT,
                required=True,
            ),
            CoordField(
                field_id="doc_date",
                page=0,
                bbox=BBox(50, h - 175, 250, h - 150),
                baseline=h - 168,
                font="FormFillAllowed",
                size=11,
                max_chars=10,
                formatter="date_ru",
                alphabet="date_digits",
                regex=r"^\d{2}\.\d{2}\.\d{4}$|^\d{4}-\d{2}-\d{2}$",
                overflow_strategy=OverflowStrategy.REJECT,
                required=True,
            ),
            CoordField(
                field_id="notes",
                page=0,
                bbox=BBox(55, h - 275, 445, h - 215),
                baseline=h - 230,
                font="FormFillAllowed",
                size=10,
                max_chars=40,
                max_lines=3,
                alphabet="cyrillic_latin_digits",
                overflow_strategy=OverflowStrategy.WRAP,
                required=False,
            ),
            CoordField(
                field_id="signature",
                page=0,
                bbox=BBox(50, 40, 250, 70),
                baseline=50,
                font="FormFillAllowed",
                size=10,
                reserved_for=ReservedFor.SIGNATURE,
                user_editable=False,
                prohibited_auto_fill=True,
                value_source=ValueSource.NONE,
            ),
            CoordField(
                field_id="stamp",
                page=0,
                bbox=BBox(300, 40, 420, 70),
                baseline=50,
                font="FormFillAllowed",
                size=10,
                reserved_for=ReservedFor.STAMP,
                user_editable=False,
                prohibited_auto_fill=True,
                value_source=ValueSource.NONE,
            ),
            CoordField(
                field_id="organ_mark",
                page=0,
                bbox=BBox(400, 100, 540, 120),
                baseline=105,
                font="FormFillAllowed",
                size=9,
                value_source=ValueSource.ORGAN,
                user_editable=False,
                prohibited_auto_fill=True,
                reserved_for=ReservedFor.ORGAN,
            ),
        ]
        return CoordinateMap(version="coord.v1", page_count=1, fields=fields, page_boxes=under.page_boxes)

    def _medical_coord_map(self, under: UnderlayBuild) -> CoordinateMap:
        h = under.page_boxes[0][3]
        fields = [
            CoordField(
                field_id="visit_date",
                page=0,
                bbox=BBox(50, h - 185, 250, h - 155),
                baseline=h - 175,
                font="FormFillAllowed",
                size=11,
                max_chars=10,
                formatter="date_ru",
                alphabet="date_digits",
                regex=r"^\d{2}\.\d{2}\.\d{4}$|^\d{4}-\d{2}-\d{2}$",
                overflow_strategy=OverflowStrategy.REJECT,
                required=True,
            ),
            CoordField(
                field_id="questions",
                page=0,
                bbox=BBox(55, h - 330, 535, h - 230),
                baseline=h - 250,
                font="FormFillAllowed",
                size=10,
                max_chars=48,
                max_lines=6,
                alphabet="cyrillic_latin_digits",
                overflow_strategy=OverflowStrategy.WRAP,
                required=False,
            ),
            CoordField(
                field_id="notes",
                page=1,
                bbox=BBox(55, 90, 535, h - 160),
                baseline=h - 180,
                font="FormFillAllowed",
                size=10,
                max_chars=52,
                max_lines=12,
                alphabet="cyrillic_latin_digits",
                overflow_strategy=OverflowStrategy.WRAP,
                required=False,
            ),
        ]
        return CoordinateMap(version="coord.v1", page_count=2, fields=fields, page_boxes=under.page_boxes)

    def submit_coord_map_for_review(
        self,
        *,
        form_version_id: UUID,
        map_json: str,
        author_id: str,
    ) -> CoordMapDraft:
        ver = self.versions.get(form_version_id)
        if not ver:
            raise FillError("not_found", "FormVersion not found", http_status=404)
        # Validate JSON parses
        CoordinateMap.from_json(map_json)
        draft = CoordMapDraft(
            id=uuid4(),
            form_version_id=form_version_id,
            author_id=author_id,
            map_json=map_json,
            status="awaiting_second_review",
        )
        self.coord_drafts[draft.id] = draft
        ver.review_status = "awaiting_second_review"
        self._persist_version(ver)
        return draft

    def approve_coord_map(self, draft_id: UUID, *, reviewer_id: str) -> FormVersionRecord:
        draft = self.coord_drafts.get(draft_id)
        if not draft:
            raise FillError("not_found", "Coord map draft not found", http_status=404)
        if draft.status != "awaiting_second_review":
            raise FillError("not_awaiting", "Draft not awaiting second review")
        if reviewer_id == draft.author_id:
            raise FillError("four_eyes", "Second reviewer must differ from author", http_status=403)
        ver = self.versions[draft.form_version_id]
        cmap = CoordinateMap.from_json(draft.map_json)
        ver.coord_map = cmap
        ver.coord_map_hash = cmap.content_hash()
        ver.second_reviewer_id = reviewer_id
        ver.review_status = "published"
        ver.published_at = utcnow()
        draft.status = "approved"
        draft.second_reviewer_id = reviewer_id
        self._persist_version(ver)
        return ver

    def preview(self, form_version_id: UUID, answers: dict[str, str]) -> PreviewResult:
        ver = self._require_generatable(form_version_id)
        return validate_inputs(ver.coord_map, answers, form_slug=ver.slug, field_schema=ver.field_schema)

    def generate(self, *, form_version_id: UUID, user_id: UUID, answers: dict[str, str]) -> GeneratedFormRecord:
        ver = self._require_generatable(form_version_id)
        preview = validate_inputs(ver.coord_map, answers, form_slug=ver.slug, field_schema=ver.field_schema)
        if not preview.ok:
            raise FillError("validation_failed", "Исправьте ошибки полей перед генерацией", http_status=422)
        answers = {**answers, **preview.normalized}
        # Block if bound source superseded
        if ver.source_snapshot_id and self.sources:
            snap = self.sources.snapshots.get(ver.source_snapshot_id)
            if snap and snap.state != SourceState.APPROVED:
                raise FillError(
                    "source_not_approved", "Bound source not approved — generation blocked", http_status=409
                )
            # If a newer approved snapshot exists for same source → block new gens
            if snap:
                latest_approved = self.sources.approved_snapshot(snap.source_id)
                if latest_approved and latest_approved.id != snap.id:
                    ver.review_status = "blocked_for_new"
                    ver.blocked_reason = "official source superseded by newer approved snapshot"
                    raise FillError("version_blocked", "FormVersion blocked for new documents", http_status=409)

        result: FillResult = fill_pdf(
            underlay_pdf=ver.original_pdf,
            underlay_hash=ver.original_hash,
            coord_map=ver.coord_map,
            answers=answers,
        )
        rec = GeneratedFormRecord(
            id=uuid4(),
            user_id=user_id,
            form_version_id=ver.id,
            catalog_form_id=ver.catalog_form_id,
            answers=dict(answers),
            template_hash=result.template_hash,
            coord_map_hash=result.coord_map_hash,
            input_hash=result.input_hash,
            output_hash=result.output_hash,
            engine_version=result.engine_version,
            output_pdf=result.output_pdf,
            preview=result.preview.to_dict(),
            audit=[
                {
                    "at": utcnow().isoformat(),
                    "action": "generate",
                    "engine_version": ENGINE_VERSION,
                    "template_hash": result.template_hash,
                    "coord_map_hash": result.coord_map_hash,
                    "input_hash": result.input_hash,
                    "output_hash": result.output_hash,
                },
            ],
        )
        self.generated[rec.id] = rec
        self._persist_generated(rec)
        return rec

    def delete_generated(self, generated_id: UUID, *, user_id: UUID) -> None:
        rec = self.generated.get(generated_id)
        if not rec or rec.user_id != user_id:
            raise FillError("not_found", "Generated form not found", http_status=404)
        rec.deleted_at = utcnow()
        rec.output_pdf = b""
        rec.audit.append({"at": utcnow().isoformat(), "action": "user_delete"})
        self.generated[generated_id] = rec
        self._persist_generated(rec)

    def get_generated(self, generated_id: UUID, *, user_id: UUID) -> GeneratedFormRecord:
        rec = self.generated.get(generated_id)
        if not rec or rec.user_id != user_id or rec.deleted_at:
            raise FillError("not_found", "Generated form not found", http_status=404)
        return rec

    def block_version_for_new(self, form_version_id: UUID, reason: str) -> FormVersionRecord:
        ver = self.versions.get(form_version_id)
        if not ver:
            raise FillError("not_found", "FormVersion not found", http_status=404)
        ver.review_status = "blocked_for_new"
        ver.blocked_reason = reason
        self._persist_version(ver)
        return ver

    def _require_generatable(self, form_version_id: UUID) -> FormVersionRecord:
        ver = self.versions.get(form_version_id)
        if not ver:
            raise FillError("not_found", "FormVersion not found", http_status=404)
        if ver.review_status == "blocked_for_new":
            raise FillError("version_blocked", "FormVersion blocked for new documents", http_status=409)
        if ver.review_status != "published":
            raise FillError("not_published", "Unconfirmed FormVersion cannot be generated", http_status=409)
        on = date.today()
        if on < ver.valid_from or (ver.valid_to and on > ver.valid_to):
            raise FillError("not_effective", "FormVersion outside effective interval", http_status=409)
        kind = inferred_form_kind(ver.slug)
        if kind == "government_form":
            assert_government_generatable(ver, catalog=self.catalog, sources=self.sources)
        else:
            assert_font_ready()
            if not ver.original_pdf:
                raise FillError("official_pdf_missing", "Файл шаблона отсутствует.", http_status=409)
        return ver

    def version_card(self, ver: FormVersionRecord) -> dict[str, Any]:
        return {
            "id": str(ver.id),
            "slug": ver.slug,
            "form_version": ver.form_version,
            "title": ver.title,
            "catalog_form_id": str(ver.catalog_form_id) if ver.catalog_form_id else None,
            "original_hash": ver.original_hash,
            "coord_map_version": ver.coord_map.version,
            "coord_map_hash": ver.coord_map_hash,
            "allowed_font_hash": ver.allowed_font_hash,
            "font_license": ver.font_license,
            "review_status": ver.review_status,
            "valid_from": ver.valid_from.isoformat(),
            "valid_to": ver.valid_to.isoformat() if ver.valid_to else None,
            "author_id": ver.author_id,
            "second_reviewer_id": ver.second_reviewer_id,
            "blocked_reason": ver.blocked_reason,
            "fields": [f.to_dict() for f in ver.coord_map.fields],
            "engine": ENGINE_VERSION,
            "kind": inferred_form_kind(ver.slug),
            "download_basename": download_stem(ver.slug),
        }

    def generated_card(self, rec: GeneratedFormRecord, *, catalog_title: str | None = None) -> dict[str, Any]:
        ver = self.versions.get(rec.form_version_id)
        return {
            "id": str(rec.id),
            "catalog_form_id": str(rec.catalog_form_id) if rec.catalog_form_id else None,
            "catalog_title": catalog_title,
            "form_version_id": str(rec.form_version_id),
            "form_version": ver.form_version if ver else None,
            "form_title": ver.title if ver else None,
            "template_hash": rec.template_hash,
            "output_hash": rec.output_hash,
            "created_at": rec.created_at.isoformat(),
            "preview_ok": bool(rec.preview.get("ok")),
            "kind": "generated",
        }

    def draft_card(self, rec: FormDraftRecord, *, catalog_title: str | None = None) -> dict[str, Any]:
        ver = self.versions.get(rec.form_version_id)
        return {
            "id": str(rec.id),
            "catalog_form_id": str(rec.catalog_form_id),
            "catalog_title": catalog_title,
            "form_version_id": str(rec.form_version_id),
            "form_version": ver.form_version if ver else None,
            "updated_at": rec.updated_at.isoformat(),
            "kind": "draft",
        }
