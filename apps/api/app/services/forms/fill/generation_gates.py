"""Fail-closed eligibility for official government forms."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from app.services.forms.fill.engine import FillError
from app.services.forms.fill.fonts import bundled_font_status
from app.services.sources.registry import SourceState
from app.services.sources.url_policy import UrlPolicyError, validate_url

SYNTHETIC_SLUG_PREFIX = "test.synthetic."
SYNTHETIC_MARKER = b"source:test-synthetic-underlay|not-an-official-form"
WORKSHEET_MARKER = b"source:service-worksheet|not-an-official-form"


def is_test_synthetic_slug(slug: str) -> bool:
    return slug.startswith(SYNTHETIC_SLUG_PREFIX)


DOWNLOAD_STEMS = {
    "medical.visit.memo": "pamyatka-vizit",
    "worksheet.mvd.patent.application": "chernovik-zayavlenie-patent",
    "worksheet.mvd.arrival_notice.app4": "chernovik-uvedomlenie-pribytie",
    "worksheet.mvd.work_notification": "chernovik-uvedomlenie-trud",
    "worksheet.mvd.rvp.application": "chernovik-zayavlenie-rvp",
    "worksheet.mvd.vnz.application": "chernovik-zayavlenie-vnzh",
    "worksheet.mvd.invitation.business": "chernovik-hodataystvo-priglashenie",
    "worksheet.mvd.stay_extension": "chernovik-zayavlenie-prodlenie",
}


def download_stem(slug: str) -> str:
    if slug in DOWNLOAD_STEMS:
        return DOWNLOAD_STEMS[slug]
    kind = inferred_form_kind(slug)
    if kind == "medical_memo":
        return "pamyatka-vizit"
    if kind == "service_worksheet":
        return "chernovik-svedeniy"
    return "document"


def inferred_form_kind(slug: str) -> str:
    if is_test_synthetic_slug(slug):
        return "synthetic_test"
    if slug.startswith("medical."):
        return "medical_memo"
    if slug.startswith("worksheet."):
        return "service_worksheet"
    return "government_form"


def act_metadata_complete(rec: Any) -> bool:
    return bool(getattr(rec, "act_number", None) and getattr(rec, "act_title", None) and getattr(rec, "act_date", None))


def government_catalog_fill_ready(rec: Any) -> bool:
    on = date.today()
    start = getattr(rec, "valid_from", None)
    end = getattr(rec, "valid_to", None)
    return bool(
        getattr(rec, "form_kind", "government_form") == "government_form"
        and getattr(rec, "status", None) == "published"
        and getattr(rec, "source_snapshot_id", None)
        and act_metadata_complete(rec)
        and getattr(rec, "content_sha256", None)
        and getattr(rec, "raw_size", 0) > 0
        and getattr(rec, "reviewer", None)
        and getattr(rec, "reviewed_at", None)
        and start
        and start <= on
        and (end is None or on <= end)
    )


def clamp_catalog_fill_ready(rec: Any) -> None:
    kind = getattr(rec, "form_kind", "government_form")
    if kind == "government_form" and not government_catalog_fill_ready(rec):
        rec.fill_ready = False
    elif kind == "medical_memo" and (rec.status != "published" or not rec.fill_version_id):
        rec.fill_ready = False


def assert_font_ready() -> None:
    status = bundled_font_status()
    if not status.ok:
        raise FillError("font_not_ready", status.reason, http_status=503)


def pdf_is_synthetic_underlay(pdf: bytes) -> bool:
    """Test marker detection; service worksheets are separately rejected below."""
    return SYNTHETIC_MARKER in pdf or b"source:demo-underlay" in pdf


def _deny(code: str, message: str) -> None:
    raise FillError(code, message, http_status=409)


def assert_government_generatable(ver: Any, *, catalog: Any | None, sources: Any | None) -> None:
    assert_font_ready()
    raw_pdf = ver.original_pdf or b""
    if (
        pdf_is_synthetic_underlay(raw_pdf)
        or WORKSHEET_MARKER in raw_pdf
        or is_test_synthetic_slug(ver.slug)
        or inferred_form_kind(ver.slug) != "government_form"
    ):
        _deny("synthetic_underlay_forbidden", "Собственный или тестовый макет не является официальным бланком.")
    if not ver.source_snapshot_id:
        _deny("source_snapshot_missing", "Нет подтверждённого снимка официального источника.")
    if sources is None or catalog is None:
        _deny("verification_unavailable", "Реестр источников и каталог обязательны для проверки бланка.")
    if ver.review_status != "published":
        _deny("not_published", "Версия формы не опубликована или заблокирована.")
    on = date.today()
    if not ver.valid_from or on < ver.valid_from or (ver.valid_to and on > ver.valid_to):
        _deny("not_effective", "Версия формы не действует на текущую дату.")
    if not raw_pdf or not ver.original_hash:
        _deny("official_pdf_missing", "Официальный файл формы отсутствует.")
    actual = hashlib.sha256(raw_pdf).hexdigest()
    if actual != ver.original_hash:
        _deny("underlay_hash_mismatch", "Контрольная сумма бланка не совпадает.")
    if ver.coord_map.content_hash() != ver.coord_map_hash:
        _deny("coord_map_hash_mismatch", "Карта полей изменена после подтверждения.")
    font = bundled_font_status()
    if not ver.allowed_font_hash or ver.allowed_font_hash.lower() != (font.sha256 or "").lower():
        _deny("font_hash_mismatch", "Шрифт формы не совпадает с дистрибутивом.")
    if not ver.font_license:
        _deny("font_license_missing", "У версии формы нет сведений о лицензии шрифта.")
    if not ver.author_id or not ver.second_reviewer_id or ver.second_reviewer_id == ver.author_id:
        _deny("coord_map_not_four_eyes", "Карту полей должны подтвердить два разных редактора.")

    snap = sources.snapshots.get(ver.source_snapshot_id)
    if not snap or snap.state != SourceState.APPROVED:
        _deny("source_not_approved", "Снимок источника не подтверждён редакторами.")
    if not snap.raw or hashlib.sha256(snap.raw).hexdigest() != snap.content_hash:
        _deny("source_hash_mismatch", "Оригинал снимка источника отсутствует или повреждён.")
    try:
        validate_url(snap.final_url, cfg=sources.cfg)
    except UrlPolicyError as exc:
        raise FillError("source_url_denied", "Адрес источника не разрешён политикой.", http_status=409) from exc
    if not sources.applicable_on(snap.id, on) or not snap.valid_from:
        _deny("source_not_applicable", "Применимость источника на текущую дату не подтверждена.")
    if snap.link_status != "ok":
        _deny("source_unavailable", "Источник требует повторной проверки доступности и актуальности.")
    latest = sources.approved_snapshot(snap.source_id)
    if latest is None or latest.id != snap.id:
        _deny("version_blocked", "Официальный источник заменён или не подтверждён.")
    latest_fetched = sources.latest_snapshot(snap.source_id)
    if latest_fetched and latest_fetched.id != snap.id and latest_fetched.content_hash != snap.content_hash:
        _deny("source_changed", "Источник изменился; до проверки новой редакции генерация заблокирована.")

    if not ver.catalog_form_id:
        _deny("catalog_missing", "Версия не привязана к карточке официальной формы.")
    rec = catalog.forms.get(ver.catalog_form_id)
    if rec is None:
        _deny("catalog_missing", "Карточка каталога не найдена.")
    if not government_catalog_fill_ready(rec):
        _deny("not_published", "Карточка формы не прошла проверку реквизитов и срока действия.")
    if rec.source_snapshot_id != ver.source_snapshot_id:
        _deny("source_snapshot_missing", "Карточка и версия связаны с разными источниками.")
    raw = catalog.raw_store.get(rec.id) or b""
    if not raw or len(raw) != rec.raw_size:
        _deny("official_pdf_missing", "Оригинал формы в каталоге отсутствует или повреждён.")
    if hashlib.sha256(raw).hexdigest() != rec.content_sha256 or rec.content_sha256 != actual:
        _deny("underlay_hash_mismatch", "Подложка не совпадает с подтверждённым файлом каталога.")
    if not act_metadata_complete(snap):
        _deny("act_metadata_incomplete", "В снимке источника отсутствуют реквизиты акта.")
    if sources.forms_status.get(rec.slug) == "review":
        _deny("source_changed", "Форма ожидает повторной редакторской проверки.")


def catalog_checklist(card: dict[str, Any], *, version: Any | None = None) -> list[dict[str, Any]]:
    source = card.get("source") or {}
    has_source = bool(isinstance(source, dict) and source.get("usable_as_basis") and source.get("verified"))
    has_file = bool(card.get("has_raw") and card.get("content_sha256"))
    has_act = bool(card.get("act_number") and card.get("act_date") and card.get("act_title"))
    published = card.get("status") == "published"
    official_version = bool(version and inferred_form_kind(version.slug) == "government_form")
    two_eyes = bool(
        official_version
        and version.author_id
        and version.second_reviewer_id
        and version.second_reviewer_id != version.author_id
    )
    snapshot_ok = bool(official_version and version.source_snapshot_id and has_source)
    return [
        {"id": "official_file", "done": has_file, "label": "Официальный файл формы сохранён без изменений"},
        {"id": "source", "done": has_source, "label": "Официальный источник подтверждён на текущую дату"},
        {"id": "act", "done": has_act, "label": "Указаны номер, дата и название нормативного акта"},
        {
            "id": "visual",
            "done": published and snapshot_ok and has_file,
            "label": "Редакторы подтвердили соответствие бланка",
        },
        {"id": "map", "done": two_eyes, "label": "Карта официального бланка подтверждена двумя редакторами"},
        {
            "id": "publish",
            "done": bool(published and has_file and two_eyes and snapshot_ok and card.get("fill_ready")),
            "label": "Форма открыта для заполнения",
        },
    ]
