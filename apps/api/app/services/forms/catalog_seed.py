"""Seed eight Prompt 6 catalog cards with categories."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.services.forms.catalog import FormCatalogService, FormRecord, utcnow

CATEGORIES = {
    "entry_stay": "Въезд и пребывание",
    "work": "Работа",
    "rvp_vnz": "РВП и ВНЖ",
    "medical": "Медицинские памятки",
}

PROMPT6_CARDS: list[dict] = [
    {
        "slug": "mvd.arrival_notice.app4",
        "title": "Уведомление о прибытии иностранного гражданина",
        "organ": "МВД России",
        "purpose": "migration_registration",
        "region": "RF",
        "category": "entry_stay",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Официальный бланк ещё не подтверждён по источнику. Доступен чеклист, бланк не подставляется.",
    },
    {
        "slug": "mvd.patent.application",
        "title": "Заявление об оформлении патента",
        "organ": "МВД России",
        "purpose": "work_patent",
        "region": "RF",
        "category": "work",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Ожидается верификация официального бланка и редакции приказа.",
    },
    {
        "slug": "mvd.work_notification",
        "title": "Уведомление о заключении трудового или гражданско-правового договора",
        "organ": "МВД России",
        "purpose": "work_notification",
        "region": "RF",
        "category": "work",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Шаблон недоступен: нет подтверждённого официального файла источника.",
    },
    {
        "slug": "mvd.rvp.application",
        "title": "Заявление о выдаче разрешения на временное проживание",
        "organ": "МВД России",
        "purpose": "rvp",
        "region": "RF",
        "category": "rvp_vnz",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Требуется проверка редакции уполномоченным редактором.",
    },
    {
        "slug": "mvd.vnz.application",
        "title": "Заявление о выдаче вида на жительство",
        "organ": "МВД России",
        "purpose": "vnz",
        "region": "RF",
        "category": "rvp_vnz",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Шаблон заблокирован до проверки официального источника.",
    },
    {
        "slug": "mvd.invitation.business",
        "title": "Ходатайство о выдаче приглашения на въезд",
        "organ": "МВД России",
        "purpose": "invitation",
        "region": "RF",
        "category": "entry_stay",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Нет опубликованной версии для заполнения.",
    },
    {
        "slug": "mvd.stay_extension",
        "title": "Заявление о продлении срока временного пребывания",
        "organ": "МВД России",
        "purpose": "stay_extension",
        "region": "RF",
        "category": "entry_stay",
        "form_kind": "government_form",
        "fill_ready": False,
        "status": "needs_review",
        "warning": "Доступен только чеклист в мастере документов.",
    },
    {
        "slug": "medical.visit.memo",
        "title": "Памятка перед визитом к врачу (собственный шаблон)",
        "organ": "Сервис",
        "purpose": "medical_memo",
        "region": "RF",
        "category": "medical",
        "form_kind": "medical_memo",
        "fill_ready": False,
        "status": "published",
        "warning": "Не является медицинским документом. Не заменяет справку или заключение.",
    },
]


def ensure_prompt6_catalog(catalog: FormCatalogService) -> None:
    """Ensure all eight Prompt 6 cards exist (idempotent)."""
    for spec in PROMPT6_CARDS:
        existing = catalog.by_slug.get(spec["slug"])
        if existing:
            rec = catalog.forms.get(existing)
            if not isinstance(rec, FormRecord):
                catalog.isolate(existing, code="catalog_record_invalid", payload=type(rec).__name__)
                catalog.forms.pop(existing, None)
                _insert_card(catalog, spec)
                continue
            updates: dict = {
                "category": spec["category"],
                "form_kind": spec["form_kind"],
                "warning": spec["warning"],
                "title": spec["title"],
            }
            if spec["form_kind"] == "government_form":
                updates["fill_ready"] = False
            if spec["status"] == "published" and rec.status == "needs_review" and spec["form_kind"] == "medical_memo":
                updates["status"] = "published"
                updates["edition_note"] = rec.edition_note if rec.edition_note and rec.edition_note != "Fill v1.0.0" else "Собственный шаблон"
            if rec.edition_note == "Fill v1.0.0":
                updates["edition_note"] = "Собственный шаблон"
            catalog.update_fields(rec.id, **updates)
            continue
        _insert_card(catalog, spec)


def seed_prompt6_catalog(catalog: FormCatalogService) -> None:
    if catalog.iter_records():
        return
    for spec in PROMPT6_CARDS:
        _insert_card(catalog, spec)


def _insert_card(catalog: FormCatalogService, spec: dict) -> None:
    rec = FormRecord(
        id=uuid4(),
        slug=spec["slug"],
        title=spec["title"],
        organ=spec["organ"],
        purpose=spec["purpose"],
        region=spec["region"],
        authority=spec["organ"],
        status=spec["status"],
        source_snapshot_id=None,
        content_sha256=None,
        raw_size=0,
        act_number="856" if "arrival" in spec["slug"] else None,
        act_date=None,
        act_title="Приказ МВД России N 856 (редакция на проверке)" if "arrival" in spec["slug"] else None,
        valid_from=None,
        valid_to=None,
        reviewed_at=utcnow() if spec["status"] == "published" else None,
        reviewer="catalog_seed" if spec["status"] == "published" else None,
        warning=spec["warning"],
        edition_note="Редакция на проверке" if spec["status"] != "published" else "Собственный шаблон",
        category=spec["category"],
        form_kind=spec["form_kind"],
        fill_ready=spec["fill_ready"],
        fill_version_id=None,
    )
    catalog.put(rec)


def link_fill_version(catalog: FormCatalogService, *, slug: str, fill_version_id: UUID) -> FormRecord:
    form_id = catalog.by_slug.get(slug)
    if not form_id:
        raise KeyError(slug)
    rec = catalog.get(form_id)
    ready = rec.form_kind == "medical_memo" and rec.status == "published"
    return catalog.update_fields(form_id, fill_version_id=fill_version_id, fill_ready=ready)
