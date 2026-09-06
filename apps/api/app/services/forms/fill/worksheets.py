"""Service data worksheets for government catalog cards — not official blanks."""

from __future__ import annotations

from typing import Any

from app.services.forms.fill.coord_map import BBox, CoordField, CoordinateMap, OverflowStrategy
from app.services.forms.fill.underlay import (
    UnderlayBuild,
    build_worksheet_underlay,
    layout_worksheet_fields,
)
from app.services.forms.official_form_acts import act_for_slug

WORKSHEET_FORM_VERSION = "1.4.0"


def _f(
    field_id: str,
    label: str,
    section: str,
    section_label: str,
    *,
    required: bool = True,
    layout: str | None = None,
    max_chars: int = 80,
) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "field_id": field_id,
        "label": label,
        "section": section,
        "section_label": section_label,
        "required": required,
        "user_editable": True,
        "max_chars": max_chars,
    }
    if layout:
        spec["layout"] = layout
        if layout == "multiline":
            spec["multiline"] = True
    return spec


WORKSHEET_HEADINGS: dict[str, list[str]] = {
    "mvd.arrival_notice.app4": [
        "Уведомление о прибытии иностранного гражданина",
        "Приложение N 4 к приказу МВД России от 10.12.2020 N 856",
    ],
    "mvd.patent.application": [
        "Заявление об оформлении патента",
        "Приложение N 1 к приказу МВД России от 14.08.2017 N 635 (ред. N 679)",
    ],
    "mvd.work_notification": [
        "Приложение N 7 к приказу МВД России от 30.07.2020 N 536",
        "(в ред. приказов МВД России от 22.11.2023 N 887 и от 06.08.2025 N 552)",
        "ФОРМА 1",
        "УВЕДОМЛЕНИЕ о заключении трудового договора или гражданско-правового договора",
    ],
    "mvd.rvp.application": [
        "Заявление о выдаче разрешения на временное проживание",
        "Формы к приказу МВД России от 08.06.2020 N 407",
    ],
    "mvd.vnz.application": [
        "Заявление о выдаче вида на жительство",
        "Формы к приказу МВД России от 11.06.2020 N 417",
    ],
    "mvd.invitation.business": [
        "Ходатайство о выдаче приглашения на въезд",
        "Формы к приказу МВД России от 29.09.2020 N 677",
    ],
    "mvd.stay_extension": [
        "Заявление о продлении срока временного пребывания",
        "Состав сведений зависит от основания в 115-ФЗ",
    ],
}

WORKSHEET_FIELDS: dict[str, list[dict[str, Any]]] = {
    "mvd.arrival_notice.app4": [
        _f("last_name", "Фамилия", "person", "Иностранный гражданин"),
        _f("first_name", "Имя", "person", "Иностранный гражданин"),
        _f("citizenship", "Гражданство", "person", "Иностранный гражданин"),
        _f("identity_doc", "Документ, удостоверяющий личность", "person", "Иностранный гражданин"),
        _f("stay_address", "Адрес пребывания", "stay", "Пребывание", layout="multiline"),
        _f("host_kind", "Вид принимающей стороны", "host", "Принимающая сторона"),
        _f("host_name", "Фамилия, имя, отчество принимающей стороны", "host", "Принимающая сторона"),
    ],
    "mvd.patent.application": [
        {
            "field_id": "photo",
            "label": "Фотография",
            "layout": "photo_box",
            "section": "head",
            "section_label": "Заявление",
        },
        _f("territorial_organ", "Территориальный орган МВД", "head", "Заявление"),
        _f("petition", "Прошу оформить патент", "head", "Заявление", layout="multiline", max_chars=220),
        _f("last_name", "Фамилия", "applicant", "Заявитель"),
        _f("first_name", "Имя", "applicant", "Заявитель"),
        _f("citizenship", "Гражданство", "applicant", "Заявитель"),
        _f("identity_doc_kind", "Вид документа, удостоверяющего личность", "applicant", "Заявитель"),
        _f("identity_doc_series", "Серия документа", "applicant", "Заявитель", max_chars=12),
        _f("identity_doc_number", "Номер документа", "applicant", "Заявитель", max_chars=20),
        _f("migration_card_series", "Серия миграционной карты", "stay", "Миграционный учёт", max_chars=8),
        _f("migration_card_number", "Номер миграционной карты", "stay", "Миграционный учёт", max_chars=12),
        _f("profession", "Профессия (специальность)", "work", "Трудовая деятельность"),
        _f("work_region", "Субъект Российской Федерации", "work", "Трудовая деятельность"),
        _f("address_rf", "Адрес в Российской Федерации", "work", "Трудовая деятельность", layout="multiline"),
    ],
    "mvd.work_notification": [
        _f("territorial_organ", "Территориальный орган МВД", "head", "Куда направляется"),
        _f("employer_status", "Статус работодателя / заказчика работ (услуг)", "employer", "Работодатель / заказчик"),
        _f("okved", "Код ОКВЭД", "employer", "Работодатель / заказчик", max_chars=16),
        _f(
            "employer_full_name", "Полное наименование / ФИО", "employer", "Работодатель / заказчик", layout="multiline"
        ),
        _f("employer_reg_number", "ОГРН / ОГРНИП", "employer", "Работодатель / заказчик"),
        _f("employer_inn", "ИНН", "employer", "Работодатель / заказчик", max_chars=12),
        _f("employer_address", "Адрес", "employer", "Работодатель / заказчик", layout="multiline"),
        _f("employer_phone", "Телефон", "employer", "Работодатель / заказчик"),
        _f("last_name", "Фамилия иностранного гражданина", "worker", "Иностранный работник"),
        _f("first_name", "Имя", "worker", "Иностранный работник"),
        _f("patronymic", "Отчество (при наличии)", "worker", "Иностранный работник", required=False),
        _f("citizenship", "Гражданство", "worker", "Иностранный работник"),
        _f("birth_date", "Дата рождения", "worker", "Иностранный работник", max_chars=10),
        _f("identity_doc_kind", "Вид документа, удостоверяющего личность", "worker", "Иностранный работник"),
        _f("identity_doc_series", "Серия", "worker", "Иностранный работник", max_chars=12),
        _f("identity_doc_number", "Номер", "worker", "Иностранный работник", max_chars=20),
        _f("identity_doc_issued_date", "Дата выдачи", "worker", "Иностранный работник", max_chars=10),
        _f("identity_doc_issuer", "Кем выдан", "worker", "Иностранный работник"),
        _f(
            "permit_kind",
            "Документ на право работы (патент / разрешение)",
            "permit",
            "Разрешительный документ и договор",
        ),
        _f("permit_series", "Серия документа", "permit", "Разрешительный документ и договор", max_chars=12),
        _f("permit_number", "Номер документа", "permit", "Разрешительный документ и договор"),
        _f("profession", "Профессия (специальность, должность)", "permit", "Разрешительный документ и договор"),
        _f(
            "contract_kind",
            "Вид договора (трудовой / гражданско-правовой)",
            "permit",
            "Разрешительный документ и договор",
        ),
        _f("contract_date", "Дата заключения договора", "permit", "Разрешительный документ и договор", max_chars=10),
        _f("work_address", "Адрес места работы", "permit", "Разрешительный документ и договор", layout="multiline"),
        _f("signatory_title_name", "Должность и ФИО подписанта", "sign", "Подпись"),
    ],
    "mvd.rvp.application": [
        _f("territorial_organ", "Территориальный орган МВД", "authority", "Орган"),
        _f("last_name", "Фамилия", "applicant", "Заявитель"),
        _f("first_name", "Имя", "applicant", "Заявитель"),
        _f("patronymic", "Отчество (при наличии)", "applicant", "Заявитель", required=False),
        _f("citizenship", "Гражданство", "applicant", "Заявитель"),
        _f("birth_date", "Дата рождения", "applicant", "Заявитель", max_chars=10),
        _f("identity_doc", "Документ, удостоверяющий личность", "applicant", "Заявитель"),
        _f("address_rf", "Адрес в Российской Федерации", "stay", "Проживание", layout="multiline"),
    ],
    "mvd.vnz.application": [
        _f("territorial_organ", "Территориальный орган МВД", "authority", "Орган"),
        _f("last_name", "Фамилия", "applicant", "Заявитель"),
        _f("first_name", "Имя", "applicant", "Заявитель"),
        _f("patronymic", "Отчество (при наличии)", "applicant", "Заявитель", required=False),
        _f("citizenship", "Гражданство", "applicant", "Заявитель"),
        _f("birth_date", "Дата рождения", "applicant", "Заявитель", max_chars=10),
        _f("identity_doc", "Документ, удостоверяющий личность", "applicant", "Заявитель"),
        _f("address_rf", "Адрес в Российской Федерации", "stay", "Проживание", layout="multiline"),
    ],
    "mvd.invitation.business": [
        _f("inviting_org", "Приглашающая организация", "invitation", "Приглашающая сторона", layout="multiline"),
        _f("last_name", "Фамилия приглашаемого", "person", "Приглашаемое лицо"),
        _f("first_name", "Имя", "person", "Приглашаемое лицо"),
        _f("citizenship", "Гражданство", "person", "Приглашаемое лицо"),
        _f("purpose", "Цель въезда", "invitation", "Приглашающая сторона"),
        _f("entry_dates", "Предполагаемые сроки пребывания", "stay", "Пребывание"),
    ],
    "mvd.stay_extension": [
        _f("last_name", "Фамилия", "person", "Заявитель"),
        _f("first_name", "Имя", "person", "Заявитель"),
        _f("citizenship", "Гражданство", "person", "Заявитель"),
        _f("stay_until", "Срок пребывания по действующему учёту", "extension", "Продление", max_chars=10),
        _f("basis", "Основание продления", "extension", "Продление", layout="multiline"),
        _f("address", "Адрес пребывания", "stay", "Пребывание", layout="multiline"),
    ],
}


def _schema_from_fields(fields: list[dict[str, Any]]) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    for spec in fields:
        if spec.get("layout") == "photo_box":
            continue
        schema[spec["field_id"]] = {
            "label": spec["label"],
            "section": spec["section"],
            "section_label": spec["section_label"],
            "required": bool(spec.get("required", True)),
            "user_editable": True,
            "multiline": spec.get("layout") == "multiline" or bool(spec.get("multiline")),
        }
    return schema


def _coord_map(
    under: UnderlayBuild, fields: list[dict[str, Any]], pages: list[list[dict[str, float | str]]]
) -> CoordinateMap:
    by_id = {spec["field_id"]: spec for spec in fields if spec.get("layout") != "photo_box"}
    cmap_fields: list[CoordField] = []
    for page_i, page_items in enumerate(pages):
        for item in page_items:
            if str(item.get("kind") or "field") != "field":
                continue
            field_id = str(item["field_id"])
            spec = by_id.get(field_id) or {}
            multiline = spec.get("layout") == "multiline" or bool(spec.get("multiline"))
            cmap_fields.append(
                CoordField(
                    field_id=field_id,
                    page=page_i,
                    bbox=BBox(
                        float(item["line_x0"]),
                        float(item["box_y0"]),
                        float(item["line_x1"]),
                        float(item["box_y1"]),
                    ),
                    baseline=float(item["line_y"]),
                    font="FormFillSans",
                    size=9,
                    max_chars=int(spec.get("max_chars", 80)),
                    max_lines=4 if multiline else 1,
                    alphabet="cyrillic_latin_digits",
                    overflow_strategy=OverflowStrategy.WRAP if multiline else OverflowStrategy.REJECT,
                    required=bool(spec.get("required", True)),
                ),
            )
    return CoordinateMap(
        version="1.0",
        page_count=len(under.page_boxes),
        fields=cmap_fields,
        page_boxes=list(under.page_boxes),
    )


def build_worksheet_pack(slug: str, title: str) -> tuple[UnderlayBuild, CoordinateMap, dict[str, Any]]:
    fields = WORKSHEET_FIELDS.get(slug)
    if not fields:
        raise KeyError(slug)
    heading = list(WORKSHEET_HEADINGS.get(slug) or [title])
    act = act_for_slug(slug) or {}
    source_line = " · ".join(
        part for part in (str(act.get("act_title") or ""), str(act.get("official_url") or "")) if part
    )
    under = build_worksheet_underlay(title=title, source_line=source_line, fields=fields, heading=heading)
    photo = any(spec.get("layout") == "photo_box" for spec in fields)
    heading_count = len([line for line in heading if line]) + (1 if source_line else 0)
    pages = layout_worksheet_fields(fields, photo=photo, heading_count=heading_count)
    return under, _coord_map(under, fields, pages), _schema_from_fields(fields)
