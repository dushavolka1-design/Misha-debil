"""Honest generation capability snapshot for UI diagnostics."""

from __future__ import annotations

from typing import Any

from app.services.forms.fill.fonts import bundled_font_status
from app.services.forms.fill.generation_gates import government_catalog_fill_ready


def generation_capabilities(*, catalog: Any, fill: Any) -> dict[str, Any]:
    font = bundled_font_status()
    catalog_ready = False
    try:
        catalog_ready = bool(catalog.typed_catalog_ok())
    except Exception:
        catalog_ready = False
    fill_engine_ready = False
    try:
        from app.services.forms.fill.engine import ENGINE_VERSION

        fill_engine_ready = bool(ENGINE_VERSION) and font.ok
    except Exception:
        fill_engine_ready = False
    official_count = 0
    medical_ready = False
    for rec in catalog.iter_records():
        if rec.form_kind == "government_form" and rec.fill_ready and government_catalog_fill_ready(rec):
            official_count += 1
        if rec.form_kind == "medical_memo" and rec.fill_ready and rec.fill_version_id:
            medical_ready = True
    reasons: list[str] = []
    if not catalog_ready:
        reasons.append("Каталог шаблонов не загружен.")
    if not font.ok:
        reasons.append(font.reason)
    if not fill_engine_ready:
        reasons.append("Движок заполнения недоступен без проверенного шрифта.")
    generation_ready = catalog_ready and font.ok and fill_engine_ready and (official_count > 0 or medical_ready)
    if catalog_ready and font.ok and fill_engine_ready and not generation_ready:
        reasons.append("Нет шаблона, который можно заполнить: государственные бланки ждут официальной проверки.")
    return {
        "catalog_ready": catalog_ready,
        "fill_engine_ready": fill_engine_ready,
        "font_ready": font.ok,
        "official_templates_count": official_count,
        "generation_ready": generation_ready,
        "medical_memo_ready": medical_ready,
        "reasons": reasons,
        "font_reason": font.reason,
    }
