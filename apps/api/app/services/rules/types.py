from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ResultKind(StrEnum):
    OBSERVED_TEXT = "observed_text"
    STRUCTURAL_CONFLICT = "structural_conflict"
    REVIEW_QUESTION = "review_question"
    NORMATIVE_CLAIM = "normative_claim"


class Severity(StrEnum):
    """Manual review priority — not a legal qualification."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Uncertainty(StrEnum):
    OK = "ok"
    UNCERTAIN = "uncertain"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_DATA = "insufficient_data"


FORBIDDEN_PHRASES = (
    "договор незаконен",
    "договор законен",
    "договор безопасен",
    "договор небезопасен",
    "contract is illegal",
    "contract is safe",
    "legal and safe",
)


@dataclass(frozen=True)
class RuleTestCase:
    case_id: str
    facts: list[dict[str, Any]]
    expect_trigger: bool
    expect_uncertainty: Uncertainty | None = None
    note: str = ""


@dataclass(frozen=True)
class RuleDef:
    rule_id: str
    version: str
    applicability: tuple[str, ...]
    required_facts: tuple[str, ...]
    severity: Severity
    severity_rationale: str
    official_sources: tuple[str, ...]  # source snapshot ids / codes
    message_template: str
    reviewer: str
    result_kind: ResultKind
    test_cases: tuple[RuleTestCase, ...] = ()
    description: str = ""


@dataclass
class RuleHit:
    rule_id: str
    rule_version: str
    result_kind: ResultKind
    severity: Severity
    severity_rationale: str
    message: str
    uncertainty: Uncertainty
    citations: list[dict[str, Any]] = field(default_factory=list)
    basis_fact_keys: list[str] = field(default_factory=list)
    official_sources: list[str] = field(default_factory=list)
    # Never a legal verdict field


def assert_safe_message(text: str) -> None:
    lower = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower:
            raise ValueError(f"Forbidden legal-verdict phrasing: {phrase}")
