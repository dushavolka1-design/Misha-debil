"""Field/bbox metrics — not subjective answer quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldMetric:
    entity_type: str
    expected: int
    predicted: int
    matched: int

    @property
    def precision(self) -> float:
        return self.matched / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.matched / self.expected if self.expected else 0.0


def bbox_iou(a: dict[str, float], b: dict[str, float]) -> float:
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix1, iy1 = max(a["x"], b["x"]), max(a["y"], b["y"])
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def match_findings(
    expected: list[dict[str, Any]],
    predicted: list[dict[str, Any]],
    *,
    iou_threshold: float = 0.5,
) -> dict[str, Any]:
    by_type: dict[str, FieldMetric] = {}
    types = sorted({e["entity_type"] for e in expected} | {p["entity_type"] for p in predicted})
    for et in types:
        exp = [e for e in expected if e["entity_type"] == et]
        pred = [p for p in predicted if p["entity_type"] == et]
        used: set[int] = set()
        matched = 0
        for e in exp:
            for j, p in enumerate(pred):
                if j in used:
                    continue
                same_page = e.get("citation", {}).get("page") == p.get("citation", {}).get("page")
                iou = bbox_iou(e["citation"]["bbox"], p["citation"]["bbox"]) if same_page else 0.0
                raw_ok = e.get("raw_text", "").strip() == p.get("raw_text", "").strip()
                if same_page and (iou >= iou_threshold or raw_ok):
                    matched += 1
                    used.add(j)
                    break
        by_type[et] = FieldMetric(et, len(exp), len(pred), matched)

    micro_exp = sum(m.expected for m in by_type.values())
    micro_pred = sum(m.predicted for m in by_type.values())
    micro_match = sum(m.matched for m in by_type.values())
    return {
        "by_field": {
            k: {
                "expected": v.expected,
                "predicted": v.predicted,
                "matched": v.matched,
                "precision": v.precision,
                "recall": v.recall,
            }
            for k, v in by_type.items()
        },
        "micro": {
            "precision": micro_match / micro_pred if micro_pred else 0.0,
            "recall": micro_match / micro_exp if micro_exp else 0.0,
        },
    }
