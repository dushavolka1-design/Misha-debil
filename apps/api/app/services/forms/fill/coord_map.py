"""Coordinate map schema for pixel-perfect form fill."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class OverflowStrategy(StrEnum):
    CLIP = "clip"
    REJECT = "reject"
    WRAP = "wrap"
    # shrink_to_fit explicitly forbidden


class ValueSource(StrEnum):
    USER = "user"
    FACT = "fact"
    ORGAN = "organ"
    MANUAL_ONLY = "manual_only"
    NONE = "none"


class ReservedFor(StrEnum):
    SIGNATURE = "signature"
    STAMP = "stamp"
    ORGAN = "organ"
    NONE = "none"


@dataclass(frozen=True)
class BBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)


@dataclass(frozen=True)
class CoordField:
    field_id: str
    page: int  # 0-based
    bbox: BBox
    baseline: float
    font: str
    size: float
    alignment: str = "left"  # left|center|right
    max_chars: int = 80
    max_lines: int = 1
    alphabet: str | None = None  # e.g. "cyrillic_latin_digits"
    regex: str | None = None
    formatter: str = "plain"  # plain|date_iso|date_ru|upper
    overflow_strategy: OverflowStrategy = OverflowStrategy.REJECT
    value_source: ValueSource = ValueSource.USER
    user_editable: bool = True
    required: bool = False
    prohibited_auto_fill: bool = False
    reserved_for: ReservedFor = ReservedFor.NONE

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["bbox"] = self.bbox.as_list()
        d["overflow_strategy"] = self.overflow_strategy.value
        d["value_source"] = self.value_source.value
        d["reserved_for"] = self.reserved_for.value
        return d

    @staticmethod
    def from_dict(data: dict[str, Any]) -> CoordField:
        b = data["bbox"]
        return CoordField(
            field_id=data["field_id"],
            page=int(data["page"]),
            bbox=BBox(float(b[0]), float(b[1]), float(b[2]), float(b[3])),
            baseline=float(data["baseline"]),
            font=str(data["font"]),
            size=float(data["size"]),
            alignment=str(data.get("alignment", "left")),
            max_chars=int(data.get("max_chars", 80)),
            max_lines=int(data.get("max_lines", 1)),
            alphabet=data.get("alphabet"),
            regex=data.get("regex"),
            formatter=str(data.get("formatter", "plain")),
            overflow_strategy=OverflowStrategy(data.get("overflow_strategy", "reject")),
            value_source=ValueSource(data.get("value_source", "user")),
            user_editable=bool(data.get("user_editable", True)),
            required=bool(data.get("required", False)),
            prohibited_auto_fill=bool(data.get("prohibited_auto_fill", False)),
            reserved_for=ReservedFor(data.get("reserved_for", "none")),
        )


@dataclass
class CoordinateMap:
    version: str
    page_count: int
    fields: list[CoordField] = field(default_factory=list)
    page_boxes: list[list[float]] = field(default_factory=list)  # [x0,y0,x1,y1] per page

    def to_json(self) -> str:
        payload = {
            "version": self.version,
            "page_count": self.page_count,
            "page_boxes": self.page_boxes,
            "fields": [f.to_dict() for f in self.fields],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @staticmethod
    def from_json(text: str) -> CoordinateMap:
        data = json.loads(text)
        return CoordinateMap(
            version=data["version"],
            page_count=int(data["page_count"]),
            page_boxes=list(data.get("page_boxes") or []),
            fields=[CoordField.from_dict(f) for f in data.get("fields") or []],
        )


ALPHABETS: dict[str, re.Pattern[str]] = {
    "latin": re.compile(r"^[A-Za-z0-9 \-.,/]+$"),
    "cyrillic": re.compile(r"^[А-Яа-яЁё0-9 \-.,/]+$"),
    "cyrillic_latin_digits": re.compile(r"^[A-Za-zА-Яа-яЁё0-9 \-.,/]+$"),
    "digits": re.compile(r"^[0-9]+$"),
    "date_digits": re.compile(r"^[0-9.\-/]+$"),
}


def format_value(raw: str, formatter: str) -> str:
    v = raw.strip()
    if formatter == "upper":
        return v.upper()
    if formatter == "date_iso":
        # expect YYYY-MM-DD → keep
        return v
    if formatter == "date_ru":
        # YYYY-MM-DD → DD.MM.YYYY
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
        if m:
            return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
        return v
    return v
