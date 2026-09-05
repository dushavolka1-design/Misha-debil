from __future__ import annotations

"""Output policy for AI findings — block unsupported legal/medical claims."""

import re
from typing import Any

# Hard-forbidden product phrases (AT-FR-12 / AT-X-01)
FORBIDDEN_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"заключени[ея]\s+юрист",
        r"юридическ(ая|ое)\s+(экспертиза|заключение)",
        r"вам\s+следует\s+подписать",
        r"это\s+(полностью\s+)?(законно|незаконно)",
        r"диагноз",
        r"заключени[ея]\s+врач",
        r"медицинск(ая|ое)\s+(экспертиза|заключение)",
        r"as a lawyer",
        r"legal advice:",
        r"you should sue",
    )
)

INJECTION_MARKERS: tuple[str, ...] = (
    "ignore previous instructions",
    "игнорируй предыдущие",
    "exfiltrate",
    "system prompt",
    "передай секреты",
    "disable safety",
)


def text_has_forbidden_claim(text: str) -> bool:
    return any(p.search(text or "") for p in FORBIDDEN_CLAIM_PATTERNS)


def text_has_injection_marker(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in INJECTION_MARKERS)


def finding_citation_ok(finding: dict[str, Any]) -> bool:
    cit = finding.get("citation")
    if not isinstance(cit, dict):
        return False
    if "page" not in cit or "bbox" not in cit or "quote" not in cit:
        return False
    bbox = cit["bbox"]
    if not isinstance(bbox, dict):
        return False
    for k in ("x", "y", "w", "h"):
        if k not in bbox:
            return False
    quote = str(cit.get("quote") or "").strip()
    return len(quote) > 0


def filter_displayable_findings(findings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Findings without citation or with forbidden claims are not shown."""
    ok: list[dict[str, Any]] = []
    dropped: list[str] = []
    for i, f in enumerate(findings):
        blob = " ".join(
            str(f.get(k) or "")
            for k in ("raw_text", "normalized_value", "message", "entity_type")
        )
        if text_has_forbidden_claim(blob):
            dropped.append(f"finding[{i}]:unsupported_legal_or_medical_claim")
            continue
        if not finding_citation_ok(f):
            dropped.append(f"finding[{i}]:missing_or_invalid_citation")
            continue
        ok.append(f)
    return ok, dropped
