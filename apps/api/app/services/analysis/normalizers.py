from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class NormalizeResult:
    ok: bool
    normalized: Any | None
    reason: str | None = None


_DATE_PATTERNS = [
    (re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b"), "%d.%m.%Y"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "%Y-%m-%d"),
]


def normalize_date(raw: str) -> NormalizeResult:
    text = raw.strip()
    for cre, fmt in _DATE_PATTERNS:
        m = cre.search(text)
        if not m:
            continue
        try:
            if fmt == "%d.%m.%Y":
                d = datetime.strptime(f"{m.group(1)}.{m.group(2)}.{m.group(3)}", fmt).date()
            else:
                d = datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}", fmt).date()
            return NormalizeResult(True, d.isoformat())
        except ValueError:
            return NormalizeResult(False, None, "invalid_calendar_date")
    return NormalizeResult(False, None, "date_parse_failed")


_MONEY = re.compile(
    r"(?P<amount>\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{1,2})?|\d+[.,]\d{1,2}|\d+)\s*(?P<cur>RUB|USD|EUR|₽|руб\.?)",
    re.IGNORECASE,
)


def normalize_money(raw: str) -> NormalizeResult:
    m = _MONEY.search(raw.replace("\u00a0", " "))
    if not m:
        return NormalizeResult(False, None, "money_parse_failed")
    amt = m.group("amount").replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        value = Decimal(amt)
    except InvalidOperation:
        return NormalizeResult(False, None, "money_invalid_decimal")
    cur = m.group("cur").upper().replace("₽", "RUB").replace("РУБ.", "RUB").replace("РУБ", "RUB")
    return NormalizeResult(True, {"amount": str(value), "currency": cur})


def _inn_checksum_10(digits: str) -> bool:
    coeffs = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    s = sum(int(digits[i]) * coeffs[i] for i in range(9)) % 11 % 10
    return s == int(digits[9])


def _inn_checksum_12(digits: str) -> bool:
    c1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    c2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
    n11 = sum(int(digits[i]) * c1[i] for i in range(10)) % 11 % 10
    n12 = sum(int(digits[i]) * c2[i] for i in range(11)) % 11 % 10
    return n11 == int(digits[10]) and n12 == int(digits[11])


def normalize_inn(raw: str) -> NormalizeResult:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        if not _inn_checksum_10(digits):
            return NormalizeResult(False, None, "inn_checksum_failed")
        return NormalizeResult(True, {"type": "inn", "value": digits, "checksum_ok": True})
    if len(digits) == 12:
        if not _inn_checksum_12(digits):
            return NormalizeResult(False, None, "inn_checksum_failed")
        return NormalizeResult(True, {"type": "inn", "value": digits, "checksum_ok": True})
    return NormalizeResult(False, None, "inn_length_invalid")


def normalize_ogrn(raw: str) -> NormalizeResult:
    digits = re.sub(r"\D", "", raw)
    if len(digits) not in {13, 15}:
        return NormalizeResult(False, None, "ogrn_length_invalid")
    body, check = digits[:-1], int(digits[-1])
    mod = 11 if len(digits) == 13 else 13
    expected = int(body) % mod % 10
    if expected != check:
        return NormalizeResult(False, None, "ogrn_checksum_failed")
    kind = "ogrn" if len(digits) == 13 else "ogrnip"
    return NormalizeResult(True, {"type": kind, "value": digits, "checksum_ok": True})


def _snils_checksum(digits: str) -> bool:
    # digits: 9 body + 2 check
    body = digits[:9]
    if int(body) <= 1001998:
        # legacy numbers may skip checksum — format-only accept
        return True
    s = sum(int(body[i]) * (9 - i) for i in range(9))
    if s < 100:
        check = s
    elif s in {100, 101}:
        check = 0
    else:
        check = s % 101
        if check in {100, 101}:
            check = 0
    return check == int(digits[9:11])


def normalize_snils(raw: str) -> NormalizeResult:
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 11:
        return NormalizeResult(False, None, "snils_length_invalid")
    if not _snils_checksum(digits):
        return NormalizeResult(False, None, "snils_checksum_failed")
    formatted = f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]} {digits[9:11]}"
    return NormalizeResult(True, {"type": "snils", "value": digits, "display": formatted, "checksum_ok": True})


# NOTE: These validators check format/checksum only. They never assert ownership or legal validity.
