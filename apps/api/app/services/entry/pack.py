from __future__ import annotations

"""Versioned entry decision rules — separate from UI. No invented universal foreigner list."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


class Stage(StrEnum):
    BEFORE_TRIP = "before_trip"
    AT_BORDER = "at_border"
    AFTER_ENTRY = "after_entry"
    WORK_STUDY = "work_study"
    EXTENSION_CHANGE = "extension_change"
    MEDICAL_DACTYLO = "medical_dactylo"


@dataclass(frozen=True)
class DecisionRule:
    rule_id: str
    version: str
    conditions: dict[str, Any]
    stage: Stage
    title: str
    actor: str
    prepare: str
    deadline_expression: str
    authority: str
    exceptions: str
    official_source_slugs: tuple[str, ...]
    valid_from: date
    valid_to: date | None
    reviewer: str
    outcome: str = "action_required"
    fee_source_slug: str | None = None
    requires_approved_sources: bool = True
    priority: int = 100


PACK_VERSION = "entry.decision_pack.v1"
PACK_REVIEWER = "entry_rules_reviewer_demo"

# Visa regimes — only codes from this approved catalog may be selected in UI/API
APPROVED_VISA_REGIMES: dict[str, dict[str, Any]] = {
    "visa_required": {"label": "Визовый режим (общий)", "source_slug": "mid-ru"},
    "visa_free_short": {"label": "Безвизовый короткий визит (каталог)", "source_slug": "mid-ru"},
    "eaeu": {"label": "Режим ЕАЭС (каталог)", "source_slug": "mid-ru"},
}


def _r(**kwargs: Any) -> DecisionRule:
    return DecisionRule(**kwargs)


# Synthetic structural rules for tests — texts are checklists, not promises of admission.
# Deadlines that are legally complex use region/treaty/status/unspecified expressions.
DECISION_RULES: tuple[DecisionRule, ...] = (
    _r(
        rule_id="entry.unknown_citizenship",
        version="1.0.0",
        conditions={"citizenship": "unknown"},
        stage=Stage.BEFORE_TRIP,
        title="Гражданство не определено",
        actor="заявитель",
        prepare="Уточните гражданство / статус ЛБГ по официальным документам. Автоматический список не формируется.",
        deadline_expression="unspecified",
        authority="уточняется после идентификации статуса",
        exceptions="Пока гражданство неизвестно, мастер не выдаёт выдуманный перечень.",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        outcome="unknown_case",
        priority=1,
    ),
    _r(
        rule_id="entry.visa_required.docs",
        version="1.0.0",
        conditions={"visa_regime_id": "visa_required"},
        stage=Stage.BEFORE_TRIP,
        title="Подготовка по визовому режиму (каталог)",
        actor="заявитель / приглашающая сторона",
        prepare="Проверьте актуальный перечень документов для визы на официальном ресурсе привязанного источника.",
        deadline_expression="unspecified",
        authority="консульское учреждение / уполномоченный орган (см. источник)",
        exceptions="Не обещает выдачу визы или допуск.",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        outcome="action_required",
        fee_source_slug="mid-ru",
        priority=20,
    ),
    _r(
        rule_id="entry.visa_free.short_visit",
        version="1.0.0",
        conditions={"visa_regime_id": "visa_free_short", "purpose": "tourism", "max_stay_days_lte": 90},
        stage=Stage.BEFORE_TRIP,
        title="Короткий безвизовый визит (туризм)",
        actor="заявитель",
        prepare="Уточните допустимый срок пребывания и документы по официальному источнику для вашего гражданства.",
        deadline_expression="treaty_dependent",
        authority="пограничный / миграционный контроль (см. источник)",
        exceptions="Короткий визит ≠ право на работу.",
        official_source_slugs=("mid-ru", "pravo-gov-ru"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=25,
    ),
    _r(
        rule_id="entry.eaeu.movement",
        version="1.0.0",
        conditions={"eaeu_member": True, "visa_regime_id": "eaeu"},
        stage=Stage.BEFORE_TRIP,
        title="Перемещение в рамках режима ЕАЭС (каталог)",
        actor="заявитель",
        prepare="Проверьте документы, предусмотренные режимом ЕАЭС, только по утверждённым официальным материалам.",
        deadline_expression="treaty_dependent",
        authority="уполномоченные органы сторон (см. источник)",
        exceptions="Не заменяет национальные процедуры при смене цели.",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=15,
    ),
    _r(
        rule_id="entry.border.general",
        version="1.0.0",
        conditions={"has_planned_entry_date": True},
        stage=Stage.AT_BORDER,
        title="При пересечении границы",
        actor="заявитель",
        prepare="Имейте при себе действительные проездные документы; допуск не гарантируется сервисом.",
        deadline_expression="event:border_crossing",
        authority="пограничные органы",
        exceptions="Сервис не обещает допуск через границу.",
        official_source_slugs=("pravo-gov-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=40,
    ),
    _r(
        rule_id="entry.after.migration_notice",
        version="1.0.0",
        conditions={"has_planned_entry_date": True, "citizenship_not": "unknown"},
        stage=Stage.AFTER_ENTRY,
        title="Действия после въезда (уточнить по источнику)",
        actor="принимающая сторона / заявитель",
        prepare="Проверьте обязанность уведомления/регистрации по официальному источнику; срок может зависеть от статуса и региона.",
        deadline_expression="business_days:7:from_entry",
        authority="миграционный учёт / МВД (уточнить по источнику)",
        exceptions="7 рабочих дней — иллюстрация калькулятора; ведомственный календарь может отличаться → needs_review.",
        official_source_slugs=("pravo-gov-ru", "nalog-gov-ru"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=50,
    ),
    _r(
        rule_id="entry.work.permit_check",
        version="1.0.0",
        conditions={"purpose": "work"},
        stage=Stage.WORK_STUDY,
        title="Работа: проверка разрешительных документов",
        actor="работодатель / заявитель",
        prepare="Не приступайте к работе, пока не подтверждены требования по утверждённому источнику для вашего режима.",
        deadline_expression="status_dependent",
        authority="уполномоченный орган в сфере труда/миграции (см. источник)",
        exceptions="ЕАЭС и иные режимы имеют отдельные условия.",
        official_source_slugs=("mintrud-gov-ru", "mid-ru"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=30,
    ),
    _r(
        rule_id="entry.study.enrollment",
        version="1.0.0",
        conditions={"purpose": "study"},
        stage=Stage.WORK_STUDY,
        title="Учёба: документы образовательной организации",
        actor="заявитель / вуз",
        prepare="Сверьте приглашение/зачисление и миграционные требования по официальным источникам.",
        deadline_expression="status_dependent",
        authority="образовательная организация + миграционный учёт",
        exceptions="—",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=30,
    ),
    _r(
        rule_id="entry.minor.guardian",
        version="1.0.0",
        conditions={"age_band": "minor"},
        stage=Stage.BEFORE_TRIP,
        title="Несовершеннолетний: согласие/сопровождение",
        actor="законный представитель",
        prepare="Проверьте документы согласия/сопровождения по официальному источнику; не запрашиваем лишние медданные.",
        deadline_expression="unspecified",
        authority="см. официальный источник",
        exceptions="Особые случаи — needs_review.",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=10,
    ),
    _r(
        rule_id="entry.extension.change",
        version="1.0.0",
        conditions={"plans_extension_or_change": True},
        stage=Stage.EXTENSION_CHANGE,
        title="Продление / изменение обстоятельств",
        actor="заявитель",
        prepare="При смене цели, адреса, работы — уточните процедуру до истечения текущего срока по официальному источнику.",
        deadline_expression="region_dependent",
        authority="территориальный орган (регион)",
        exceptions="Региональные различия возможны.",
        official_source_slugs=("pravo-gov-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=60,
    ),
    _r(
        rule_id="entry.medical_dactylo.if_applicable",
        version="1.0.0",
        conditions={"special_statuses_contains": "medical_dactylo_applicable"},
        stage=Stage.MEDICAL_DACTYLO,
        title="Медицинские / дактилоскопические действия (если применимы)",
        actor="заявитель",
        prepare="Выполните только если это следует из утверждённого правила для вашего статуса; сервис не ставит диагнозов.",
        deadline_expression="status_dependent",
        authority="уполномоченные организации (см. источник)",
        exceptions="Не применимо ко всем иностранцам.",
        official_source_slugs=("mintrud-gov-ru", "pravo-gov-ru"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=70,
    ),
    _r(
        rule_id="entry.family.host",
        version="1.0.0",
        conditions={"purpose": "family", "has_invitation_or_host": True},
        stage=Stage.BEFORE_TRIP,
        title="Семья / принимающая сторона",
        actor="принимающая сторона / заявитель",
        prepare="Подтвердите основания приглашения и документы принимающей стороны по официальному источнику.",
        deadline_expression="unspecified",
        authority="см. источник",
        exceptions="—",
        official_source_slugs=("mid-ru",),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        reviewer=PACK_REVIEWER,
        priority=35,
    ),
)

RULES_BY_ID = {r.rule_id: r for r in DECISION_RULES}
