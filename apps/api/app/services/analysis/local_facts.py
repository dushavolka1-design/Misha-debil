"""Deterministic fact extraction from extracted page text (no external LLM)."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

from app.services.analysis.normalizers import normalize_date, normalize_inn, normalize_ogrn, normalize_snils
from app.services.analysis.records import FindingRecord, PageRecord

MAX_FINDINGS = 80
EXCERPT_CHARS = 900

_INN = re.compile(r"\b(\d{10}|\d{12})\b")
_OGRN = re.compile(r"\b(\d{13}|\d{15})\b")
_SNILS = re.compile(r"\b(\d{3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{2})\b")
_MONEY = re.compile(
    r"(\d[\d\s\u00a0]{1,15}(?:[.,]\d{2})?)\s*(?:руб\.?|RUB|₽)",
    re.IGNORECASE,
)
_DATE = re.compile(r"\b(\d{2}[./]\d{2}[./]\d{4}|\d{4}-\d{2}-\d{2})\b")
_TITLE = re.compile(
    r"^(ДОГОВОР|СОГЛАШЕНИЕ|АКТ|ДКП|Договор|ЗАЯВЛЕНИЕ|УВЕДОМЛЕНИЕ|ПРИКАЗ|ПАМЯТКА|ХОДАТАЙСТВО)[^\n]{0,80}",
    re.IGNORECASE | re.MULTILINE,
)
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
_FIO = re.compile(r"\b([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})\b")
_PARTY = re.compile(
    r"(Работодатель|Заказчик|Исполнитель|Подрядчик|Арендодатель|Арендатор|"
    r"Покупатель|Продавец|Заявитель|Принимающая сторона|Иностранный гражданин)\s*[:\-–]\s*([^\n]{3,80})",
    re.IGNORECASE,
)
_ADDR = re.compile(
    r"(?:адрес(?:\s+места\s+нахождения)?|место\s+нахождения|зарегистрирован[аоы]?)\s*[:\-–]\s*([^\n]{8,120})",
    re.IGNORECASE,
)
_FIO_SKIP = {
    "Российская Федерация",
    "Договор аренды",
    "Договор купли",
    "Уведомление о",
}


def _cite(page: PageRecord, quote: str, line_bbox: dict[str, float] | None = None) -> dict[str, Any]:
    bbox = line_bbox or {"x": 72.0, "y": 72.0, "w": 400.0, "h": 14.0}
    return {"page": page.page_number, "bbox": bbox, "quote": quote[:500]}


def _append(findings: list[FindingRecord], rec: FindingRecord) -> None:
    if len(findings) < MAX_FINDINGS:
        findings.append(rec)


def extract_local_facts(pages: list[PageRecord]) -> list[FindingRecord]:
    findings: list[FindingRecord] = []
    text_pages = [p for p in pages if not p.error_code and p.text.strip()]
    if not text_pages:
        empty = next((p for p in pages if not p.error_code), pages[0] if pages else None)
        if empty:
            findings.append(
                FindingRecord(
                    id=uuid4(),
                    kind="inference",
                    entity_type="doc.extract",
                    raw_text="Текст не извлечён",
                    normalized_value=(
                        "На этом компьютере не удалось прочитать текст. "
                        "Если это скан, нужен файл с текстовым слоем или более чёткое изображение."
                    ),
                    confidence=0.4,
                    uncertainty_state="low_ocr",
                    citation=_cite(empty, "Текст не извлечён"),
                ),
            )
        return findings

    joined = "\n".join(p.text for p in text_pages)
    excerpt = " ".join(joined.split())[:EXCERPT_CHARS]
    if excerpt:
        _append(
            findings,
            FindingRecord(
                id=uuid4(),
                kind="fact",
                entity_type="doc.excerpt",
                raw_text=excerpt,
                normalized_value=excerpt,
                confidence=0.7,
                uncertainty_state="ok",
                citation=_cite(text_pages[0], excerpt[:240]),
            ),
        )

    seen_inn: set[str] = set()
    seen_ogrn: set[str] = set()
    seen_snils: set[str] = set()
    seen_fio: set[str] = set()
    seen_money: set[str] = set()
    seen_email: set[str] = set()
    seen_phone: set[str] = set()
    title_done = False

    for page in text_pages:
        text = page.text
        if not title_done:
            m = _TITLE.search(text)
            if m:
                q = " ".join(m.group(0).split())
                _append(
                    findings,
                    FindingRecord(
                        id=uuid4(),
                        kind="inference",
                        entity_type="doc.title",
                        raw_text=q,
                        normalized_value=q,
                        confidence=0.72,
                        uncertainty_state="ok",
                        citation=_cite(page, q),
                    ),
                )
                title_done = True
        for m in _PARTY.finditer(text):
            role = m.group(1).strip()
            name = " ".join(m.group(2).split())
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="inference",
                    entity_type="party.role",
                    raw_text=m.group(0).strip(),
                    normalized_value={"role": role, "name": name[:120]},
                    confidence=0.7,
                    uncertainty_state="ok",
                    citation=_cite(page, m.group(0).strip()[:240]),
                ),
            )
        for m in _ADDR.finditer(text):
            q = " ".join(m.group(1).split())
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.address",
                    raw_text=q,
                    normalized_value=q,
                    confidence=0.66,
                    uncertainty_state="ok",
                    citation=_cite(page, q[:240]),
                ),
            )
        for m in _INN.finditer(text):
            q = m.group(1)
            if q in seen_inn:
                continue
            parsed = normalize_inn(q)
            if not parsed.ok:
                continue
            seen_inn.add(q)
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.identifier",
                    raw_text=q,
                    normalized_value=parsed.normalized,
                    confidence=0.85,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _OGRN.finditer(text):
            q = m.group(1)
            if q in seen_ogrn:
                continue
            parsed = normalize_ogrn(q)
            if not parsed.ok:
                continue
            seen_ogrn.add(q)
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.identifier",
                    raw_text=q,
                    normalized_value=parsed.normalized,
                    confidence=0.82,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _SNILS.finditer(text):
            q = m.group(1)
            parsed = normalize_snils(q)
            if not parsed.ok:
                continue
            key = str(parsed.normalized["value"]) if isinstance(parsed.normalized, dict) else q
            if key in seen_snils:
                continue
            seen_snils.add(key)
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.identifier",
                    raw_text=q,
                    normalized_value=parsed.normalized,
                    confidence=0.8,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _MONEY.finditer(text):
            q = m.group(0).strip()
            if q in seen_money:
                continue
            seen_money.add(q)
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="amount.value",
                    raw_text=q,
                    normalized_value=q,
                    confidence=0.8,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _DATE.finditer(text):
            q = m.group(1)
            parsed = normalize_date(q.replace("/", "."))
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="doc.date.sign",
                    raw_text=q,
                    normalized_value=parsed.normalized if parsed.ok else q,
                    confidence=0.78 if parsed.ok else 0.6,
                    uncertainty_state="ok" if parsed.ok else "ambiguous",
                    citation=_cite(page, q),
                ),
            )
        for m in _EMAIL.finditer(text):
            q = m.group(0)
            if q.lower() in seen_email:
                continue
            seen_email.add(q.lower())
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.email",
                    raw_text=q,
                    normalized_value=q,
                    confidence=0.8,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _PHONE.finditer(text):
            q = m.group(0)
            compact = re.sub(r"\D", "", q)
            if compact in seen_phone:
                continue
            seen_phone.add(compact)
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="fact",
                    entity_type="party.phone",
                    raw_text=q,
                    normalized_value=q,
                    confidence=0.74,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
        for m in _FIO.finditer(text):
            q = m.group(1)
            if len(q.split()) < 2 or q in _FIO_SKIP or q.lower() in seen_fio:
                continue
            if any(q.startswith(skip) for skip in _FIO_SKIP):
                continue
            seen_fio.add(q.lower())
            _append(
                findings,
                FindingRecord(
                    id=uuid4(),
                    kind="inference",
                    entity_type="party.name",
                    raw_text=q,
                    normalized_value=q,
                    confidence=0.62,
                    uncertainty_state="ok",
                    citation=_cite(page, q),
                ),
            )
            if len(seen_fio) >= 12:
                break
    return findings


def ai_unavailable_finding() -> FindingRecord:
    return FindingRecord(
        id=uuid4(),
        kind="inference",
        entity_type="analysis.capability",
        raw_text="Локальный разбор выполнен",
        normalized_value=(
            "Файл обработан на этом компьютере: распознавание текста, извлечение фактов "
            "и проверка правил. Расширенная модель сейчас не подключена."
        ),
        confidence=1.0,
        uncertainty_state="ok",
        citation={"page": 1, "bbox": {"x": 0, "y": 0, "w": 0, "h": 0}, "quote": ""},
    )
