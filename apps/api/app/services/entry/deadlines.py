"""Deadline calculator — never pretends complex legal calendars are a single integer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class DeadlineKind(StrEnum):
    CALENDAR_DAYS = "calendar_days"
    BUSINESS_DAYS = "business_days"
    EVENT_RELATIVE = "event_relative"
    REGION_DEPENDENT = "region_dependent"
    TREATY_DEPENDENT = "treaty_dependent"
    STATUS_DEPENDENT = "status_dependent"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True)
class DeadlineResult:
    kind: DeadlineKind
    expression: str
    timezone: str
    absolute_date: date | None
    explanation: str
    needs_review: bool
    certainty: str  # certain|approximate|unknown


# Simple RU business-day skip Sat/Sun — NOT a substitute for regional/authority calendars
_WEEKEND = {5, 6}


def _add_business_days(start: date, days: int) -> date:
    d = start
    left = days
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() not in _WEEKEND:
            left -= 1
    return d


def calculate_deadline(
    expression: str,
    *,
    anchor: date | None,
    timezone: str = "Europe/Moscow",
    region_code: str | None = None,
    context: dict | None = None,
) -> DeadlineResult:
    """
    Parse expressions like:
      calendar_days:7:from_entry
      business_days:7:from_entry
      event:border_crossing+calendar_days:7
      region_dependent
      treaty_dependent
      status_dependent
      unspecified
    """
    _ctx = context or {}
    tz = timezone
    # Validate timezone
    try:
        ZoneInfo(tz)
    except Exception:
        tz = "Europe/Moscow"

    expr = (expression or "unspecified").strip().lower()

    if expr in {"unspecified", ""}:
        return DeadlineResult(
            DeadlineKind.UNSPECIFIED,
            expression=expr or "unspecified",
            timezone=tz,
            absolute_date=None,
            explanation="Срок не задан простым числом; требуется уточнение по официальному источнику.",
            needs_review=True,
            certainty="unknown",
        )

    if expr.startswith("region_dependent"):
        return DeadlineResult(
            DeadlineKind.REGION_DEPENDENT,
            expression=expr,
            timezone=tz,
            absolute_date=None,
            explanation=(
                f"Срок зависит от региона ({region_code or 'не указан'}) "
                f"и локальных правил — не сводится к одному числу."
            ),
            needs_review=True,
            certainty="unknown",
        )

    if expr.startswith("treaty_dependent"):
        return DeadlineResult(
            DeadlineKind.TREATY_DEPENDENT,
            expression=expr,
            timezone=tz,
            absolute_date=None,
            explanation="Срок зависит от международного договора / режима — проверьте утверждённый источник.",
            needs_review=True,
            certainty="unknown",
        )

    if expr.startswith("status_dependent"):
        return DeadlineResult(
            DeadlineKind.STATUS_DEPENDENT,
            expression=expr,
            timezone=tz,
            absolute_date=None,
            explanation="Срок зависит от статуса лица — без утверждённого правила абсолютная дата не вычисляется.",
            needs_review=True,
            certainty="unknown",
        )

    if not anchor:
        return DeadlineResult(
            DeadlineKind.EVENT_RELATIVE,
            expression=expr,
            timezone=tz,
            absolute_date=None,
            explanation="Якорная дата события не задана; абсолютный срок не вычислен.",
            needs_review=True,
            certainty="unknown",
        )

    # calendar_days:N:from_entry | business_days:N:from_entry
    parts = expr.split(":")
    if len(parts) >= 2 and parts[0] in {"calendar_days", "business_days"}:
        try:
            n = int(parts[1])
        except ValueError:
            return DeadlineResult(
                DeadlineKind.UNSPECIFIED,
                expression=expr,
                timezone=tz,
                absolute_date=None,
                explanation="Некорректное выражение срока.",
                needs_review=True,
                certainty="unknown",
            )
        if parts[0] == "calendar_days":
            abs_d = anchor + timedelta(days=n)
            return DeadlineResult(
                DeadlineKind.CALENDAR_DAYS,
                expression=expr,
                timezone=tz,
                absolute_date=abs_d,
                explanation=(
                    f"{n} календарных дней от {anchor.isoformat()} "
                    f"(таймзона {tz}). Не учитывает специальные календарные исключения органа."
                ),
                needs_review=False,
                certainty="approximate",
            )
        abs_d = _add_business_days(anchor, n)
        return DeadlineResult(
            DeadlineKind.BUSINESS_DAYS,
            expression=expr,
            timezone=tz,
            absolute_date=abs_d,
            explanation=(
                f"{n} рабочих дней (пн–пт) от {anchor.isoformat()} в {tz}. "
                "Региональные/ведомственные нерабочие дни не включены — при необходимости needs_review."
            ),
            needs_review=True,
            certainty="approximate",
        )

    if expr.startswith("event:"):
        return DeadlineResult(
            DeadlineKind.EVENT_RELATIVE,
            expression=expr,
            timezone=tz,
            absolute_date=None,
            explanation=(
                f"Срок привязан к событию ({expr}); абсолютная "
                f"дата без подтверждённого события не фиксируется."
            ),
            needs_review=True,
            certainty="unknown",
        )

    return DeadlineResult(
        DeadlineKind.UNSPECIFIED,
        expression=expr,
        timezone=tz,
        absolute_date=None,
        explanation="Неизвестное выражение срока.",
        needs_review=True,
        certainty="unknown",
    )


def now_in_tz(timezone: str = "Europe/Moscow") -> datetime:
    try:
        return datetime.now(ZoneInfo(timezone))
    except Exception:
        return datetime.now(ZoneInfo("Europe/Moscow"))
