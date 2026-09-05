from __future__ import annotations

"""Build immutable A4 PDFs for test underlays and the service medical memo."""

import hashlib
import io
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.forms.fill.fonts import resolve_allowed_font

A4_W, A4_H = A4  # 595.27 x 841.89
SYNTHETIC_MARKER = b"source:test-synthetic-underlay|not-an-official-form"
SYNTHETIC_TITLE = "TEST SYNTHETIC UNDERLAY — not an official form"

MEDICAL_BANNER = "ПАМЯТКА СЕРВИСА. НЕ ЯВЛЯЕТСЯ СПРАВКОЙ ИЛИ ЗАКЛЮЧЕНИЕМ."
MEDICAL_BANNER_EN = "SERVICE MEMO. NOT A CERTIFICATE, CONCLUSION, STAMP, SIGNATURE, QR, OR DIAGNOSIS."
WORKSHEET_BANNER = "ЧЕРНОВИК СВЕДЕНИЙ СЕРВИСА. НЕ БЛАНК МВД И НЕ ОФИЦИАЛЬНАЯ ФОРМА."
WORKSHEET_MARKER = b"source:service-worksheet|not-an-official-form"
PHOTO_BOX_LABEL = "Цветная фотография 30×40 мм"


@dataclass(frozen=True)
class UnderlayBuild:
    pdf_bytes: bytes
    content_hash: str
    page_boxes: list[list[float]]
    static_labels: list[str]


def _register_fill_font() -> str:
    font_path = resolve_allowed_font()
    font_name = "FormFillSans"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    return font_name


def build_demo_a4_underlay(*, title: str = SYNTHETIC_TITLE) -> UnderlayBuild:
    """Deterministic A4 PDF for tests only. Never an official government blank."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    font_name = _register_fill_font()

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.rect(36, 36, A4_W - 72, A4_H - 72)
    c.setFont(font_name, 14)
    c.drawString(50, A4_H - 60, title)
    c.setFont(font_name, 10)
    c.drawString(50, A4_H - 90, "Static label: Full name")
    c.line(50, A4_H - 110, 400, A4_H - 110)
    c.drawString(50, A4_H - 140, "Static label: Date")
    c.line(50, A4_H - 160, 250, A4_H - 160)
    c.drawString(50, A4_H - 190, "Static label: Notes (multiline)")
    c.rect(50, A4_H - 280, 400, 70)
    c.drawString(50, 80, "Signature area (leave empty)")
    c.rect(50, 40, 200, 30)
    c.drawString(300, 80, "Stamp area (leave empty)")
    c.rect(300, 40, 120, 30)
    c.setFont(font_name, 8)
    c.drawString(50, 20, SYNTHETIC_MARKER.decode("ascii"))
    c.showPage()
    c.save()
    data = buf.getvalue()
    return UnderlayBuild(
        pdf_bytes=data,
        content_hash=hashlib.sha256(data).hexdigest(),
        page_boxes=[[0, 0, float(A4_W), float(A4_H)]],
        static_labels=[
            title,
            "Static label: Full name",
            "Static label: Date",
            "Static label: Notes (multiline)",
            "Signature area (leave empty)",
            "Stamp area (leave empty)",
            SYNTHETIC_MARKER.decode("ascii"),
        ],
    )


def _draw_medical_banners(c: canvas.Canvas, font_name: str) -> None:
    c.saveState()
    c.setFillColorRGB(0.75, 0.12, 0.12)
    c.setFont(font_name, 16)
    c.drawCentredString(A4_W / 2, A4_H - 42, MEDICAL_BANNER)
    c.setFont(font_name, 9)
    c.drawCentredString(A4_W / 2, A4_H - 58, MEDICAL_BANNER_EN)
    c.setFillColorRGB(0.85, 0.85, 0.85)
    c.setFont(font_name, 22)
    c.translate(A4_W / 2, A4_H / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "НЕ СПРАВКА / НЕ ЗАКЛЮЧЕНИЕ")
    c.restoreState()
    c.setFillColorRGB(0.75, 0.12, 0.12)
    c.setFont(font_name, 11)
    c.drawCentredString(A4_W / 2, 28, MEDICAL_BANNER)
    c.setFillColorRGB(0, 0, 0)


def build_medical_memo_underlay() -> UnderlayBuild:
    """Own service template: large marking on every page, no stamp/signature/QR/diagnosis."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    font_name = _register_fill_font()

    _draw_medical_banners(c, font_name)
    c.setFont(font_name, 16)
    c.drawString(50, A4_H - 90, "Памятка перед визитом к врачу")
    c.setFont(font_name, 10)
    c.drawString(50, A4_H - 112, "Собственный шаблон сервиса. Не документ учреждения.")
    c.drawString(50, A4_H - 150, "Дата визита")
    c.line(50, A4_H - 170, 250, A4_H - 170)
    c.drawString(50, A4_H - 200, "Вопросы врачу (ваши формулировки, без диагноза)")
    c.rect(50, A4_H - 340, 495, 120)
    c.drawString(50, 80, "Нет печати, подписи, QR-кода, номера учреждения и диагноза.")
    c.showPage()

    _draw_medical_banners(c, font_name)
    c.setFont(font_name, 14)
    c.drawString(50, A4_H - 90, "Дополнительные заметки к визиту")
    c.setFont(font_name, 10)
    c.drawString(50, A4_H - 112, "Только ваши заметки. Это не направление и не результат обследования.")
    c.rect(50, 80, 495, A4_H - 220)
    c.showPage()
    c.save()
    data = buf.getvalue()
    return UnderlayBuild(
        pdf_bytes=data,
        content_hash=hashlib.sha256(data).hexdigest(),
        page_boxes=[[0, 0, float(A4_W), float(A4_H)], [0, 0, float(A4_W), float(A4_H)]],
        static_labels=[
            MEDICAL_BANNER,
            "Памятка перед визитом к врачу",
            "Дата визита",
            "Вопросы врачу (ваши формулировки, без диагноза)",
            "Нет печати, подписи, QR-кода, номера учреждения и диагноза.",
            "Дополнительные заметки к визиту",
        ],
    )


def wrap_label(text: str, width: int = 88) -> list[str]:
    words = str(text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if len(trial) <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [str(text or "")]


def layout_worksheet_fields(
    fields: list[dict[str, str]],
    *,
    photo: bool = False,
    heading_count: int = 2,
) -> list[list[dict[str, float | str]]]:
    """Stack labeled lines on A4. Origin bottom-left to match the fill engine."""
    drawable = [spec for spec in fields if spec.get("layout") != "photo_box"]
    pages: list[list[dict[str, float | str]]] = []
    current: list[dict[str, float | str]] = []
    extra = max(0, heading_count - 2) * 11
    y = (A4_H - 188) if photo else (A4_H - 118 - extra)
    bottom = 40
    last_section = ""

    def new_page() -> None:
        nonlocal current, y, last_section
        if current:
            pages.append(current)
        current = []
        y = A4_H - 72
        last_section = ""

    for spec in drawable:
        multiline = spec.get("layout") == "multiline" or spec.get("multiline")
        height = 36 if multiline else 14
        gap = 16
        section = str(spec.get("section_label") or "")
        new_section = bool(section and section != last_section)
        header_h = 22 if new_section else 0
        label_lines = wrap_label(str(spec.get("label") or ""))
        label_h = 10 * len(label_lines)
        block = header_h + label_h + 6 + height + gap
        if y - block < bottom:
            new_page()
            header_h = 22 if section else 0
            new_section = bool(section)
            block = header_h + label_h + 6 + height + gap
        if new_section:
            current.append(
                {
                    "kind": "section",
                    "label": section,
                    "label_x": 48,
                    "label_y": y,
                },
            )
            y -= header_h
            last_section = section
        label_y = y
        y_line = y - label_h - 4
        current.append(
            {
                "kind": "field",
                "field_id": spec["field_id"],
                "label": spec["label"],
                "label_lines": label_lines,
                "label_x": 48,
                "label_y": label_y,
                "line_x0": 48,
                "line_x1": A4_W - 48,
                "line_y": y_line,
                "box_y0": y_line - (height - 12 if multiline else 4),
                "box_y1": y_line + (2 if multiline else 12),
            },
        )
        y = y_line - (height - 10 if multiline else 4) - gap
    if current:
        pages.append(current)
    return pages or [[]]


def _draw_photo_box(c: canvas.Canvas, font_name: str) -> None:
    width, height = 85.05, 113.4  # 30×40 mm
    x = A4_W - 48 - width
    y = A4_H - 58 - height
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1)
    c.rect(x, y, width, height)
    c.setFont(font_name, 7)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.drawCentredString(x + width / 2, y + height / 2 + 8, "30×40 мм")
    c.drawCentredString(x + width / 2, y + height / 2 - 6, "цветная фотография")
    c.setFillColorRGB(0, 0, 0)


def build_worksheet_underlay(
    *,
    title: str,
    source_line: str,
    fields: list[dict[str, str]],
    heading: list[str] | None = None,
) -> UnderlayBuild:
    """Service data sheet. Legal status lives in the user agreement, not on the page."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    font_name = _register_fill_font()
    photo = any(spec.get("layout") == "photo_box" for spec in fields)
    heading_lines = [line for line in (heading or [title]) if line]
    heading_count = len(heading_lines) + (1 if source_line else 0)
    pages = layout_worksheet_fields(fields, photo=photo, heading_count=heading_count)
    labels = list(heading_lines) + ([source_line] if source_line else [])
    if photo:
        labels.append(PHOTO_BOX_LABEL)

    for page_index, page_fields in enumerate(pages):
        c.setTitle(title[:80])
        c.setAuthor("Docly")
        c.setSubject(WORKSHEET_MARKER.decode("ascii"))
        c.setFillColorRGB(0, 0, 0)
        y_head = A4_H - 36
        annex_heading = any("Приложение" in line for line in heading_lines)
        if page_index == 0:
            drawn_heading = heading_lines
        elif annex_heading:
            drawn_heading = ["ФОРМА 1. Продолжение"]
        else:
            drawn_heading = heading_lines[:1]
        for index, line in enumerate(drawn_heading):
            upper = line.upper()
            if "ФОРМА 1" in upper:
                size = 12
            elif annex_heading and "УВЕДОМЛЕНИЕ" in upper:
                size = 10
            elif annex_heading:
                size = 8
            elif index == 0:
                size = 12
            else:
                size = 8
            c.setFont(font_name, size)
            c.drawString(48, y_head, line[:96])
            y_head -= 11
        if page_index == 0 and source_line:
            c.setFont(font_name, 7)
            for chunk_i, start in enumerate(range(0, min(len(source_line), 240), 96)):
                c.drawString(48, y_head - chunk_i * 9, source_line[start : start + 96])
        if photo and page_index == 0:
            _draw_photo_box(c, font_name)
        for item in page_fields:
            kind = str(item.get("kind") or "field")
            if kind == "section":
                c.setFont(font_name, 10)
                c.setFillColorRGB(0.12, 0.12, 0.12)
                c.drawString(float(item["label_x"]), float(item["label_y"]), str(item["label"])[:86])
                labels.append(str(item["label"]))
                continue
            c.setFont(font_name, 8)
            c.setFillColorRGB(0, 0, 0)
            line_list = item.get("label_lines") or wrap_label(str(item["label"]))
            for line_i, line in enumerate(line_list):
                c.drawString(float(item["label_x"]), float(item["label_y"]) - line_i * 10, str(line)[:96])
            c.setStrokeColorRGB(0.35, 0.35, 0.35)
            y0 = float(item["box_y0"])
            y1 = float(item["box_y1"])
            if y1 - y0 > 20:
                c.rect(48, y0, A4_W - 96, y1 - y0, stroke=1, fill=0)
            else:
                c.line(float(item["line_x0"]), float(item["line_y"]), float(item["line_x1"]), float(item["line_y"]))
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.setFont(font_name, 8)
        c.drawString(48, 18, "Docly")
        c.showPage()

    c.save()
    data = buf.getvalue()
    if WORKSHEET_MARKER not in data:
        data = data + b"\n%" + WORKSHEET_MARKER
    page_boxes = [[0.0, 0.0, float(A4_W), float(A4_H)] for _ in pages]
    return UnderlayBuild(
        pdf_bytes=data,
        content_hash=hashlib.sha256(data).hexdigest(),
        page_boxes=page_boxes,
        static_labels=labels,
    )
