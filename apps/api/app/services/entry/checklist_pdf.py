"""Informational checklist PDF — never an official government form."""

from __future__ import annotations

import io
from collections.abc import Sequence

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.forms.fill.fonts import resolve_allowed_font

A4_W, A4_H = A4
CHECKLIST_BANNER = "ИНФОРМАЦИОННЫЙ ЧЕКЛИСТ СЕРВИСА. НЕ ЯВЛЯЕТСЯ ОФИЦИАЛЬНОЙ ФОРМОЙ."
CHECKLIST_MARKER = b"informational-checklist|not-an-official-form"
_FONT_NAME = "ChecklistSans"


def _register_font() -> str:
    path = resolve_allowed_font()
    if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_FONT_NAME, str(path)))
    return _FONT_NAME


def _wrap(c: canvas.Canvas, text: str, font: str, size: int, max_width: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if c.stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_checklist_pdf(
    *,
    title: str,
    steps: Sequence[str],
    documents: Sequence[str],
    official_source: str,
    reviewed_at: str,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    font = _register_font()
    y = A4_H - 48
    max_w = A4_W - 96

    def block(heading: str, lines: Sequence[str], *, size: int = 10) -> None:
        nonlocal y
        if y < 80:
            c.showPage()
            y = A4_H - 48
        c.setFont(font, 12)
        c.setFillColorRGB(0.55, 0.05, 0.05)
        c.drawString(48, y, heading)
        y -= 18
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont(font, size)
        for raw in lines or ["—"]:
            for piece in _wrap(c, str(raw), font, size, max_w):
                if y < 56:
                    c.showPage()
                    y = A4_H - 48
                    c.setFont(font, size)
                c.drawString(48, y, piece)
                y -= 14
        y -= 10

    c.setFillColorRGB(0.55, 0.05, 0.05)
    c.setFont(font, 11)
    for banner_line in _wrap(c, CHECKLIST_BANNER, font, 11, max_w):
        c.drawString(48, y, banner_line)
        y -= 16
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont(font, 16)
    y -= 8
    for title_line in _wrap(c, title, font, 16, max_w):
        c.drawString(48, y, title_line)
        y -= 20
    c.setFont(font, 10)
    c.drawString(48, y, f"Дата проверки: {reviewed_at or 'уточняется'}")
    y -= 24

    numbered = [f"{idx}. {step}" for idx, step in enumerate(steps, start=1)]
    block("Шаги", numbered or ["По выбранным ответам шаги не сформированы."])
    block("Документы", documents or ["Список документов уточняется по официальному источнику."])
    block("Официальный источник", [official_source or "Источник уточняется."])
    block("Маркировка", [CHECKLIST_BANNER, "Informational checklist. Not an official form."])

    c.setFont(font, 8)
    c.setFillColorRGB(0.45, 0.1, 0.1)
    c.drawCentredString(A4_W / 2, 28, CHECKLIST_BANNER)
    c.save()

    data = buf.getvalue()
    comment = b"% " + CHECKLIST_BANNER.encode("utf-8") + b"\n% " + CHECKLIST_MARKER + b"\n"
    nl = data.find(b"\n")
    if nl != -1:
        data = data[: nl + 1] + comment + data[nl + 1 :]
    return data
