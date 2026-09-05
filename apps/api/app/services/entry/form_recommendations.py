"""Map entry wizard answers to applicable catalog form cards."""

from __future__ import annotations

from typing import Any

from app.services.entry.engine import Questionnaire
from app.services.forms.catalog import FormCatalogService


def recommend_catalog_forms(catalog: FormCatalogService, q: Questionnaire) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    slug_rules: list[tuple[str, str, bool]] = [
        (
            "mvd.arrival_notice.app4",
            "После въезда в РФ обычно требуется уведомление о прибытии для постановки на мигучёт.",
            q.purpose in {"tourism", "study", "family", "other"}
            and not q.eaeu_member
            and (q.planned_stay_days or 0) >= 7,
        ),
        (
            "mvd.patent.application",
            "Для работы по найму часто нужен патент (если не действует безвиз/ЕАЭС).",
            q.purpose == "work" and not q.eaeu_member,
        ),
        (
            "mvd.work_notification",
            "При трудоустройстве работодатель уведомляет МВД о договоре.",
            q.purpose == "work",
        ),
        (
            "mvd.rvp.application",
            "Длительное пребывание или переход к РВП — отдельное заявление.",
            q.plans_extension_or_change and (q.planned_stay_days or 0) > 90,
        ),
        (
            "mvd.vnz.application",
            "Вид на жительство — отдельный статус, не заменяет временное пребывание.",
            q.plans_extension_or_change and q.purpose in {"family", "work"},
        ),
        (
            "mvd.invitation.business",
            "Приглашение может понадобиться для визы или визита принимающей стороны.",
            q.invitation or q.host_type in {"individual", "org"},
        ),
        (
            "mvd.stay_extension",
            "Продление срока пребывания оформляется отдельным заявлением.",
            q.plans_extension_or_change,
        ),
        (
            "medical.visit.memo",
            "Памятка помогает подготовиться к медосмотру; не заменяет справку.",
            "medical_dactylo_applicable" in q.special_statuses or q.purpose in {"work", "study"},
        ),
    ]
    for slug, reason, applicable in slug_rules:
        if not applicable:
            continue
        form_id = catalog.by_slug.get(slug)
        if not form_id:
            continue
        rec = catalog.forms[form_id]
        card = catalog.card(rec)
        out.append(
            {
                "form_id": str(rec.id),
                "slug": rec.slug,
                "title": rec.title,
                "reason": reason,
                "fill_ready": rec.fill_ready,
                "form_kind": rec.form_kind,
                "unavailable_reason": catalog.unavailable_reason(rec),
                "category_label": card.get("category_label"),
            },
        )
    return out
