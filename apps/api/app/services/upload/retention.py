from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class RetentionPolicy:
    """Placeholders — real calendar days come from RETENTION_*_NEEDS_REVIEW config."""

    original_days: int
    normalized_render_days: int
    extracted_text_days: int
    report_days: int
    audit_days: int


DEFAULT_RETENTION = RetentionPolicy(
    original_days=30,  # RETENTION_ORIGINALS_NEEDS_REVIEW
    normalized_render_days=60,  # RETENTION_REPORTS_NEEDS_REVIEW
    extracted_text_days=60,
    report_days=90,
    audit_days=365,
)

# Shorter retention for medical uploads (RETENTION_MEDICAL_*_NEEDS_REVIEW)
MEDICAL_RETENTION = RetentionPolicy(
    original_days=7,
    normalized_render_days=7,
    extracted_text_days=7,
    report_days=14,
    audit_days=365,
)


def expires_at(created: datetime, days: int) -> datetime:
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created + timedelta(days=days)


def retention_for_kind(policy: RetentionPolicy, kind: str) -> int:
    return {
        "original": policy.original_days,
        "quarantine": policy.original_days,
        "normalized_render": policy.normalized_render_days,
        "extracted_text": policy.extracted_text_days,
        "report": policy.report_days,
        "audit": policy.audit_days,
    }.get(kind, policy.original_days)


def policy_for_upload(
    *,
    potentially_medical: bool,
    default: RetentionPolicy = DEFAULT_RETENTION,
    medical: RetentionPolicy = MEDICAL_RETENTION,
) -> RetentionPolicy:
    return medical if potentially_medical else default
