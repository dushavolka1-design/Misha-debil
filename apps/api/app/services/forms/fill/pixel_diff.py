"""Pixel-diff report for form fill CI — mask approved bboxes; outside ≈ 0."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageDraw

from app.services.forms.fill.coord_map import CoordinateMap, ReservedFor

# Antialias / merge soft edges: documented technical tolerance (absolute RGB delta)
TECHNICAL_TOLERANCE = 2


@dataclass
class PageDiffResult:
    page_index: int
    outside_max_delta: int
    outside_changed_pixels: int
    inside_changed_pixels: int
    page_box_match: bool
    passed: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class PixelDiffReport:
    dpi: int
    tolerance: int
    pages: list[PageDiffResult]
    page_count_match: bool
    static_text_notes: list[str]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "dpi": self.dpi,
            "tolerance": self.tolerance,
            "page_count_match": self.page_count_match,
            "passed": self.passed,
            "static_text_notes": self.static_text_notes,
            "pages": [asdict(p) for p in self.pages],
        }

    def write_artifact(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _render_pdf(pdf_bytes: bytes, *, dpi: int) -> list[Image.Image]:
    doc = pdfium.PdfDocument(pdf_bytes)
    scale = dpi / 72.0
    images: list[Image.Image] = []
    for i in range(len(doc)):
        page = doc[i]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        images.append(pil.convert("RGB"))
    return images


def _pdf_to_px(bbox: list[float], page_height_pt: float, dpi: int) -> tuple[int, int, int, int]:
    """Convert PDF user-space bbox (origin bottom-left) to PIL top-left pixels."""
    scale = dpi / 72.0
    x0, y0, x1, y1 = bbox
    left = int(x0 * scale)
    right = int(x1 * scale)
    top = int((page_height_pt - y1) * scale)
    bottom = int((page_height_pt - y0) * scale)
    return left, top, right, bottom


def _mask_from_map(
    size: tuple[int, int],
    coord_map: CoordinateMap,
    page_index: int,
    page_height_pt: float,
    dpi: int,
    pad: int = 3,
) -> Image.Image:
    """White = inside approved fillable bboxes (ignored for outside-diff)."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for f in coord_map.fields:
        if f.page != page_index:
            continue
        if f.reserved_for in {ReservedFor.SIGNATURE, ReservedFor.STAMP}:
            continue
        left, top, right, bottom = _pdf_to_px(f.bbox.as_list(), page_height_pt, dpi)
        draw.rectangle([left - pad, top - pad, right + pad, bottom + pad], fill=255)
    return mask


def compare_underlay_vs_output(
    *,
    underlay_pdf: bytes,
    output_pdf: bytes,
    coord_map: CoordinateMap,
    dpi: int = 150,
    tolerance: int = TECHNICAL_TOLERANCE,
    underlay_text: list[str] | None = None,
    output_text: list[str] | None = None,
) -> PixelDiffReport:
    orig_imgs = _render_pdf(underlay_pdf, dpi=dpi)
    out_imgs = _render_pdf(output_pdf, dpi=dpi)
    page_count_match = len(orig_imgs) == len(out_imgs) == coord_map.page_count

    pages: list[PageDiffResult] = []
    all_ok = page_count_match
    for i, (a, b) in enumerate(zip(orig_imgs, out_imgs, strict=False)):
        if a.size != b.size:
            pages.append(
                PageDiffResult(
                    page_index=i,
                    outside_max_delta=255,
                    outside_changed_pixels=-1,
                    inside_changed_pixels=-1,
                    page_box_match=False,
                    passed=False,
                    notes=["raster size mismatch"],
                ),
            )
            all_ok = False
            continue

        page_h = coord_map.page_boxes[i][3] if i < len(coord_map.page_boxes) else 841.89
        mask = _mask_from_map(a.size, coord_map, i, page_h, dpi)
        inv = Image.eval(mask, lambda px: 255 - px)

        diff = ImageChops.difference(a, b)
        # composite(image1, image2, mask): mask white → image1, black → image2
        black = Image.new("RGB", a.size, (0, 0, 0))
        outside = Image.composite(diff, black, inv)  # outside fillable zones
        inside = Image.composite(diff, black, mask)  # inside approved bboxes

        outside_max = 0
        outside_changed = 0
        inside_changed = 0
        # Use load() to avoid getdata deprecation and speed
        ox = outside.load()
        ix = inside.load()
        w, h = a.size
        for y in range(h):
            for x in range(w):
                op = ox[x, y]
                if op != (0, 0, 0):
                    outside_changed += 1
                    outside_max = max(outside_max, max(op))
                ip = ix[x, y]
                if ip != (0, 0, 0):
                    inside_changed += 1

        box_match = True
        if i < len(coord_map.page_boxes):
            # page box checked at PDF level by caller; raster aspect sanity
            expected_w = int((coord_map.page_boxes[i][2] - coord_map.page_boxes[i][0]) * dpi / 72)
            expected_h = int((coord_map.page_boxes[i][3] - coord_map.page_boxes[i][1]) * dpi / 72)
            box_match = abs(a.size[0] - expected_w) <= 2 and abs(a.size[1] - expected_h) <= 2

        passed = outside_max <= tolerance and box_match
        notes = []
        if outside_max > tolerance:
            notes.append(
                f"outside mask max delta {outside_max} > tolerance {tolerance} "
                f"(technical antialias allowance documented)",
            )
        if inside_changed == 0 and any(f.page == i and f.reserved_for == ReservedFor.NONE for f in coord_map.fields):
            # may be empty fill — ok
            notes.append("no inside-mask pixel changes (empty or invisible fill)")

        # Baseline/clipping soft check: inside changes should stay within mask (by construction)
        notes.append("clipping enforced by fill engine clipPath; inside deltas expected for filled fields")

        pages.append(
            PageDiffResult(
                page_index=i,
                outside_max_delta=int(outside_max),
                outside_changed_pixels=outside_changed,
                inside_changed_pixels=inside_changed,
                page_box_match=box_match,
                passed=passed,
                notes=notes,
            ),
        )
        all_ok = all_ok and passed

    text_notes: list[str] = []
    if underlay_text is not None and output_text is not None:
        for i, (u, o) in enumerate(zip(underlay_text, output_text, strict=False)):
            # Static labels from underlay must still appear in output extraction
            for label in ("Static label", "source:demo-underlay", "Signature area", "Stamp area"):
                if label in u and label not in o:
                    text_notes.append(f"page {i}: static text missing after fill: {label}")
                    all_ok = False
            text_notes.append(f"page {i}: underlay_len={len(u)} output_len={len(o)}")

    return PixelDiffReport(
        dpi=dpi,
        tolerance=tolerance,
        pages=pages,
        page_count_match=page_count_match,
        static_text_notes=text_notes,
        passed=all_ok,
    )
