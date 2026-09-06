"""Domain checks for user-entered form answers — spelling, dummy values, eligibility."""

from __future__ import annotations

import re
from typing import Any

from app.services.forms.fill.validate import FieldIssue

_RF_CITIZENSHIP = re.compile(
    r"(российск|россия\b|\bрф\b|russian\s+federation|\brussia\b)",
    re.IGNORECASE,
)
_PASSPORT_TYPO = re.compile(r"пасспорт", re.IGNORECASE)
_DUMMY_SEQ = re.compile(r"^(?:0123456789|1234567890|9876543210|0{6,}|1{6,}|9{6,})$")
_JUNK = re.compile(r"^(test|тест|asdf|qwerty|xxx|n/?a|foo|bar)$", re.IGNORECASE)
_MIGRATION_SERIES = re.compile(r"^\d{4}$")
_MIGRATION_NUMBER = re.compile(r"^\d{7}$")
_PASSPORT_TYPO_SUB = re.compile(r"пасспорт", re.IGNORECASE)

PETITION_PATENT = "Прошу оформить патент на осуществление трудовой деятельности в Российской Федерации"

_FOREIGN_WORKER_SLUGS = {
    "mvd.patent.application",
    "mvd.work_notification",
    "mvd.rvp.application",
    "mvd.vnz.application",
    "mvd.invitation.business",
    "mvd.arrival_notice.app4",
    "mvd.stay_extension",
}


def catalog_slug(form_slug: str) -> str:
    return form_slug.removeprefix("worksheet.")


def _fix_passport_typo(value: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        src = match.group(0)
        if src.isupper():
            return "ПАСПОРТ"
        if src[0].isupper():
            return "Паспорт"
        return "паспорт"

    return _PASSPORT_TYPO_SUB.sub(_repl, value)


def normalize_answers(
    form_slug: str,
    answers: dict[str, str],
    field_schema: dict[str, Any] | None = None,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Safe in-place fixes: spelling, digits-only card numbers, patent petition wording."""
    del field_schema
    slug = catalog_slug(form_slug)
    out = dict(answers)
    corrections: list[dict[str, str]] = []

    for field_id, raw in list(out.items()):
        original = raw or ""
        value = original.strip()
        if not value:
            continue
        fixed = _fix_passport_typo(value)
        if field_id in {"migration_card_series", "migration_card_number"}:
            digits = re.sub(r"\D", "", fixed)
            if digits:
                fixed = digits
        if slug == "mvd.patent.application" and field_id == "petition":
            if "прошу оформить патент" not in fixed.lower():
                fixed = PETITION_PATENT
        if fixed != original:
            out[field_id] = fixed
            if _PASSPORT_TYPO.search(original) and not _PASSPORT_TYPO.search(fixed):
                message = "Исправлено написание: «Паспорт»."
            elif field_id == "petition" and fixed == PETITION_PATENT:
                message = "Подставлена формулировка заявления об оформлении патента."
            elif field_id in {"migration_card_series", "migration_card_number"}:
                message = "Оставлены только цифры серии и номера."
            else:
                message = "Значение скорректировано."
            corrections.append(
                {"field_id": field_id, "before": original, "after": fixed, "message": message},
            )
    return out, corrections


def _text(answers: dict[str, str], *keys: str) -> str:
    for key in keys:
        val = (answers.get(key) or "").strip()
        if val:
            return val
    return ""


def check_answers(
    form_slug: str,
    answers: dict[str, str],
    field_schema: dict[str, Any] | None = None,
) -> list[FieldIssue]:
    issues: list[FieldIssue] = []
    slug = catalog_slug(form_slug)
    schema = field_schema or {}

    for field_id, raw in answers.items():
        value = (raw or "").strip()
        if not value:
            continue
        if _PASSPORT_TYPO.search(value):
            issues.append(
                FieldIssue(
                    field_id,
                    "spelling",
                    "Напишите «Паспорт», без лишней «с».",
                ),
            )
        compact = re.sub(r"\D", "", value)
        if compact and _DUMMY_SEQ.fullmatch(compact):
            issues.append(
                FieldIssue(
                    field_id,
                    "dummy_value",
                    "Похоже на вымышленный номер. Перенесите серию и номер с настоящего документа.",
                ),
            )
        if _JUNK.fullmatch(value):
            issues.append(
                FieldIssue(
                    field_id,
                    "dummy_value",
                    "Укажите реальное значение, как в документе.",
                ),
            )

    for field_id, meta in schema.items():
        if "гражданств" not in (meta.get("label") or "").lower() and "citizenship" not in field_id:
            continue
        value = _text(answers, field_id)
        if value and slug in _FOREIGN_WORKER_SLUGS and _RF_CITIZENSHIP.search(value):
            issues.append(
                FieldIssue(
                    field_id,
                    "citizenship_rf",
                    "Для этой процедуры заявитель — иностранный гражданин. "
                    "Гражданство «Российская Федерация» здесь не подходит.",
                ),
            )

    if slug == "mvd.patent.application":
        issues.extend(_patent_checks(answers))
    return issues


def _patent_checks(answers: dict[str, str]) -> list[FieldIssue]:
    issues: list[FieldIssue] = []
    petition = _text(answers, "petition")
    if petition and "прошу оформить патент" not in petition.lower():
        issues.append(
            FieldIssue(
                "petition",
                "petition_wording",
                "В заявлении должна быть формулировка «прошу оформить патент».",
            ),
        )
    kind = _text(answers, "identity_doc_kind")
    if kind and "паспорт" not in kind.lower() and "паспор" in kind.lower():
        issues.append(FieldIssue("identity_doc_kind", "spelling", "Напишите «Паспорт»."))
    series = _text(answers, "migration_card_series")
    number = _text(answers, "migration_card_number")
    if series and not _MIGRATION_SERIES.fullmatch(series):
        issues.append(
            FieldIssue(
                "migration_card_series",
                "migration_card_format",
                "Серия миграционной карты — 4 цифры, как на карте, без выдуманной последовательности.",
            ),
        )
    if number and not _MIGRATION_NUMBER.fullmatch(number):
        issues.append(
            FieldIssue(
                "migration_card_number",
                "migration_card_format",
                "Номер миграционной карты — 7 цифр с бланка карты, не произвольный набор.",
            ),
        )
    return issues
