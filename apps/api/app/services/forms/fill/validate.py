"""Preview validation for form fill — length, alphabet, required, reserved fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.forms.fill.coord_map import (
    ALPHABETS,
    CoordinateMap,
    OverflowStrategy,
    ReservedFor,
    ValueSource,
    format_value,
)


@dataclass
class FieldIssue:
    field_id: str
    code: str
    message: str
    severity: str = "error"  # error|warning|info


@dataclass
class PreviewResult:
    ok: bool
    issues: list[FieldIssue] = field(default_factory=list)
    normalized: dict[str, str] = field(default_factory=dict)
    skipped_reserved: list[str] = field(default_factory=list)
    manual_or_organ: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.__dict__ for issue in self.issues],
            "normalized": self.normalized,
            "skipped_reserved": self.skipped_reserved,
            "manual_or_organ": self.manual_or_organ,
        }


def _estimate_lines(text: str, max_chars: int, max_lines: int) -> list[str]:
    if max_lines <= 1:
        return [text]
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        cand = w if not cur else f"{cur} {w}"
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines


def validate_inputs(
    coord_map: CoordinateMap,
    answers: dict[str, str],
    *,
    form_slug: str | None = None,
    field_schema: dict[str, Any] | None = None,
) -> PreviewResult:
    issues: list[FieldIssue] = []
    skipped: list[str] = []
    manual: list[str] = []
    working = dict(answers)
    if form_slug:
        from app.services.forms.fill.answer_checks import normalize_answers

        working, _corrections = normalize_answers(form_slug, answers, field_schema)
    normalized: dict[str, str] = dict(working)

    by_id = {f.field_id: f for f in coord_map.fields}
    for f in coord_map.fields:
        if f.reserved_for in {ReservedFor.SIGNATURE, ReservedFor.STAMP}:
            skipped.append(f.field_id)
            if working.get(f.field_id):
                issues.append(
                    FieldIssue(
                        f.field_id,
                        "reserved_no_fill",
                        "Подпись/печать не размещаются движком — место оставляется пустым",
                    ),
                )
            continue
        if f.value_source in {ValueSource.ORGAN, ValueSource.MANUAL_ONLY} or f.prohibited_auto_fill:
            manual.append(f.field_id)

        raw = working.get(f.field_id, "")
        if not raw:
            if f.required:
                issues.append(FieldIssue(f.field_id, "required_empty", "Обязательное поле пусто"))
            continue

        if not f.user_editable and f.value_source == ValueSource.ORGAN:
            issues.append(
                FieldIssue(
                    f.field_id, "organ_only", "Поле заполняется органом — не редактируется пользователем", "warning"
                ),
            )

        formatted = format_value(raw, f.formatter)
        if f.alphabet and f.alphabet in ALPHABETS and not ALPHABETS[f.alphabet].fullmatch(formatted):
            issues.append(FieldIssue(f.field_id, "forbidden_chars", f"Символы вне алфавита {f.alphabet}"))
        if f.regex and not re.fullmatch(f.regex, formatted):
            issues.append(FieldIssue(f.field_id, "regex_mismatch", "Значение не соответствует regex"))

        lines = _estimate_lines(formatted, f.max_chars, f.max_lines)
        if len(formatted) > f.max_chars * f.max_lines and f.overflow_strategy == OverflowStrategy.REJECT:
            issues.append(FieldIssue(f.field_id, "overflow_length", "Превышена длина; overflow=reject"))
        if len(lines) > f.max_lines:
            if f.overflow_strategy == OverflowStrategy.REJECT:
                issues.append(FieldIssue(f.field_id, "overflow_wrap", "Не помещается по числу строк"))
            else:
                issues.append(FieldIssue(f.field_id, "wrap_applied", "Будет перенос/clip внутри bbox", "warning"))
                formatted = "\n".join(lines[: f.max_lines])
        if f.overflow_strategy == OverflowStrategy.CLIP and len(formatted) > f.max_chars * f.max_lines:
            formatted = formatted[: f.max_chars * f.max_lines]
            issues.append(FieldIssue(f.field_id, "clip_applied", "Текст обрезан по bbox", "warning"))

        # Never shrink font
        if f.size < 7:
            issues.append(FieldIssue(f.field_id, "font_too_small", "Размер шрифта ниже читаемого порога"))

        normalized[f.field_id] = formatted

    schema = field_schema or {}
    for key in working:
        if key not in by_id and key not in schema:
            issues.append(FieldIssue(key, "unknown_field", "Поле отсутствует в coordinate map", "warning"))

    if form_slug:
        from app.services.forms.fill.answer_checks import check_answers

        issues.extend(check_answers(form_slug, working, schema))

    errors = [i for i in issues if i.severity == "error"]
    return PreviewResult(
        ok=len(errors) == 0,
        issues=issues,
        normalized=normalized,
        skipped_reserved=skipped,
        manual_or_organ=manual,
    )
