from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from dar.providers.ports import OcrPageResult


@dataclass(frozen=True)
class LayoutRegion:
    region_type: str
    text: str
    page: int
    bbox: dict[str, float]
    meta: dict[str, Any]


_HEADING = re.compile(r"^(ДОГОВОР|СОГЛАШЕНИЕ|АКТ|ПРИЛОЖЕНИЕ|СПЕЦИФИКАЦИЯ|SERVICE AGREEMENT)\b", re.I)
_NUMBERED = re.compile(r"^(\d+[\).]|§\s*\d+|п\.\s*\d+)")
_TABLE = re.compile(r"\|.+\|")
_ANNEX = re.compile(r"(?i)приложен\w+|annex|attachment")
_SIGNATURE = re.compile(r"(?i)подпис\w+|signature|\/s\/")
_HANDWRITTEN_HINT = re.compile(r"(?i)рукописн|handwrit")


def detect_layout(page: OcrPageResult) -> list[LayoutRegion]:
    regions: list[LayoutRegion] = []
    for line in page.lines:
        t = line.text.strip()
        if not t:
            continue
        bbox = {"x": line.bbox.x, "y": line.bbox.y, "w": line.bbox.w, "h": line.bbox.h}
        if _HEADING.search(t):
            regions.append(LayoutRegion("heading", t, page.page_number, bbox, {}))
        elif _TABLE.search(t):
            regions.append(LayoutRegion("table_row", t, page.page_number, bbox, {}))
        elif _NUMBERED.match(t):
            regions.append(LayoutRegion("numbered_item", t, page.page_number, bbox, {}))
        elif _ANNEX.search(t):
            regions.append(LayoutRegion("annex", t, page.page_number, bbox, {}))
        elif _SIGNATURE.search(t):
            # Presence of signature block only — never treat as identity confirmation
            meta: dict[str, bool | str] = {"identity_asserted": False}
            if _HANDWRITTEN_HINT.search(t):
                meta["handwritten_detected"] = True
                meta["note"] = "Handwritten mark is not identity verification"
            regions.append(LayoutRegion("signature_block", t, page.page_number, bbox, meta))
        else:
            regions.append(LayoutRegion("paragraph", t, page.page_number, bbox, {}))
    return regions
