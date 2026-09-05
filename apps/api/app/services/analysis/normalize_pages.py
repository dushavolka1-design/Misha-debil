from __future__ import annotations

"""Page normalization metadata — originals are never mutated."""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class NormalizedPage:
    page_index: int  # 0-based
    width: float
    height: float
    rotation: int
    content_hash: str
    underlay_key: str | None = None


def normalize_pages_from_ocr(
    *,
    document_id: str,
    pages: list,
) -> list[NormalizedPage]:
    out: list[NormalizedPage] = []
    for p in pages:
        raw = f"{p.page_number}:{p.width}:{p.height}:{p.rotation}:{p.text}".encode()
        out.append(
            NormalizedPage(
                page_index=p.page_number - 1,
                width=p.width,
                height=p.height,
                rotation=p.rotation,
                content_hash=sha256(raw).hexdigest(),
                underlay_key=f"underlay/{document_id}/p{p.page_number}.meta",
            ),
        )
    return out
