"""Form fill engine — clone underlay, overlay text only in approved bboxes."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.services.forms.fill.coord_map import CoordinateMap, OverflowStrategy, ReservedFor
from app.services.forms.fill.fonts import FONT_LICENSE_NOTE, font_hash, resolve_allowed_font
from app.services.forms.fill.validate import PreviewResult, validate_inputs

ENGINE_VERSION = "form.fill.engine.v1"
MIN_READABLE_SIZE = 7.0


class FillError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass(frozen=True)
class FillResult:
    output_pdf: bytes
    output_hash: str
    template_hash: str
    coord_map_hash: str
    input_hash: str
    engine_version: str
    preview: PreviewResult
    page_count: int
    page_boxes: list[list[float]]


def _input_hash(answers: dict[str, str]) -> str:
    payload = "|".join(f"{k}={answers[k]}" for k in sorted(answers))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _register_font() -> tuple[str, str]:
    path = resolve_allowed_font()
    name = "FormFillAllowed"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, str(path)))
    return name, font_hash(path)


def _wrap_lines(text: str, max_chars: int, max_lines: int) -> list[str]:
    if max_lines <= 1:
        return [text[:max_chars]] if len(text) > max_chars else [text]
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
            cur = w[:max_chars]
            if len(lines) >= max_lines:
                return lines
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


def _draw_overlay(
    *,
    page_width: float,
    page_height: float,
    coord_map: CoordinateMap,
    page_index: int,
    values: dict[str, str],
    font_name: str,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))
    for f in coord_map.fields:
        if f.page != page_index:
            continue
        if f.reserved_for in {ReservedFor.SIGNATURE, ReservedFor.STAMP}:
            continue
        text = values.get(f.field_id)
        if not text:
            continue
        if f.size < MIN_READABLE_SIZE:
            raise FillError("font_unreadable", f"Field {f.field_id}: refuse unreadable font size")

        c.saveState()
        path = c.beginPath()
        path.rect(f.bbox.x0, f.bbox.y0, f.bbox.width, f.bbox.height)
        c.clipPath(path, stroke=0, fill=0)

        size = f.size  # no shrink-to-fit
        c.setFont(font_name, size)
        lines = _wrap_lines(text, f.max_chars, f.max_lines)
        if f.overflow_strategy == OverflowStrategy.REJECT and (
            len(text) > f.max_chars * f.max_lines or len(lines) > f.max_lines
        ):
            raise FillError("overflow", f"Field {f.field_id} overflows bbox")

        leading = size * 1.2
        y = f.baseline
        for line in lines:
            if y < f.bbox.y0:
                break
            x = f.bbox.x0
            if f.alignment == "right":
                x = f.bbox.x1 - c.stringWidth(line, font_name, size)
            elif f.alignment == "center":
                x = f.bbox.x0 + (f.bbox.width - c.stringWidth(line, font_name, size)) / 2
            c.drawString(x, y, line)
            y -= leading
        c.restoreState()
    c.save()
    return buf.getvalue()


def extract_static_text(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    out: list[str] = []
    for page in reader.pages:
        try:
            out.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            out.append("")
    return out


def page_geometry(pdf_bytes: bytes) -> list[list[float]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    boxes = []
    for page in reader.pages:
        box = page.mediabox
        boxes.append([float(box.left), float(box.bottom), float(box.right), float(box.top)])
    return boxes


def fill_pdf(
    *,
    underlay_pdf: bytes,
    underlay_hash: str,
    coord_map: CoordinateMap,
    answers: dict[str, str],
    require_preview_ok: bool = True,
) -> FillResult:
    digest = hashlib.sha256(underlay_pdf).hexdigest()
    if digest != underlay_hash:
        raise FillError("underlay_hash_mismatch", "Underlay hash must match before generation", http_status=409)

    preview = validate_inputs(coord_map, answers)
    if require_preview_ok and not preview.ok:
        raise FillError("preview_failed", "Preview validation failed", http_status=400)

    font_name, _fh = _register_font()
    reader = PdfReader(io.BytesIO(underlay_pdf))
    writer = PdfWriter()
    if reader.metadata:
        try:
            writer.add_metadata({str(k): str(v) for k, v in reader.metadata.items() if v is not None})
        except Exception:  # noqa: BLE001
            pass

    page_boxes = page_geometry(underlay_pdf)
    for i, page in enumerate(reader.pages):
        box = page.mediabox
        w, h = float(box.width), float(box.height)
        overlay_bytes = _draw_overlay(
            page_width=w,
            page_height=h,
            coord_map=coord_map,
            page_index=i,
            values=preview.normalized,
            font_name=font_name,
        )
        overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
        base = writer.add_page(page)
        if overlay_reader.pages:
            base.merge_page(overlay_reader.pages[0], over=True)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    output = out_buf.getvalue()

    if len(PdfReader(io.BytesIO(output)).pages) != len(reader.pages):
        raise FillError("page_count_changed", "Fill must not change page count")

    return FillResult(
        output_pdf=output,
        output_hash=hashlib.sha256(output).hexdigest(),
        template_hash=digest,
        coord_map_hash=coord_map.content_hash(),
        input_hash=_input_hash(answers),
        engine_version=ENGINE_VERSION,
        preview=preview,
        page_count=len(reader.pages),
        page_boxes=page_boxes,
    )


def engine_info() -> dict[str, Any]:
    from app.services.forms.fill.fonts import bundled_font_status

    font = bundled_font_status()
    return {
        "engine_version": ENGINE_VERSION,
        "font_license_note": FONT_LICENSE_NOTE,
        "min_readable_size": MIN_READABLE_SIZE,
        "shrink_to_fit": False,
        "font_ready": font.ok,
        "font_reason": font.reason,
    }
