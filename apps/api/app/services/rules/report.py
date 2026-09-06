from __future__ import annotations

"""Analytic report builder — PDF/JSON. No legal verdict language."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.services.rules.types import RuleHit, assert_safe_message

DISCLAIMER = (
    "Это информационный разбор документа, а не юридическая консультация. "
    "Severity отражает приоритет ручной проверки, а не правовую квалификацию. "
    "Сервис не утверждает, что договор «законен» или «безопасен»."
)

REPORT_VERSION = "report.schema.v1"


@dataclass
class ReportArtifact:
    id: UUID
    document_id: UUID
    user_id: UUID
    analysis_run_id: UUID | None
    created_at: datetime
    report_version: str
    pipeline_versions: dict[str, str]
    disclaimer: str
    sources: list[dict[str, str]]
    unanalyzed_pages: list[int]
    model_findings: list[dict[str, Any]]
    rule_results: list[dict[str, Any]]
    summary: dict[str, Any]


def _hit_to_dict(h: RuleHit) -> dict[str, Any]:
    assert_safe_message(h.message)
    return {
        "origin": "rule_engine",
        "rule_id": h.rule_id,
        "rule_version": h.rule_version,
        "result_kind": h.result_kind.value,
        "severity": h.severity.value,
        "severity_rationale": h.severity_rationale,
        "message": h.message,
        "uncertainty": h.uncertainty.value,
        "citations": h.citations,
        "basis_fact_keys": h.basis_fact_keys,
        "official_sources": h.official_sources,
    }


def build_report(
    *,
    document_id: UUID,
    user_id: UUID,
    analysis_run_id: UUID | None,
    model_findings: list[dict[str, Any]],
    rule_hits: list[RuleHit],
    sources: list[dict[str, str]] | None = None,
    unanalyzed_pages: list[int] | None = None,
    pipeline_versions: dict[str, str] | None = None,
) -> ReportArtifact:
    for f in model_findings:
        # model findings stay tagged separately from rules
        f.setdefault("origin", "model_inference")
    return ReportArtifact(
        id=uuid4(),
        document_id=document_id,
        user_id=user_id,
        analysis_run_id=analysis_run_id,
        created_at=datetime.now(timezone.utc),
        report_version=REPORT_VERSION,
        pipeline_versions=pipeline_versions or {},
        disclaimer=DISCLAIMER,
        sources=sources
        or [
            {"code": "SRC.CONSISTENCY.v1", "title": "Consistency checklist (editorial)"},
            {"code": "SRC.PD.152FZ.v1", "title": "PD processing notes (needs legal pack review)"},
        ],
        unanalyzed_pages=unanalyzed_pages or [],
        model_findings=model_findings,
        rule_results=[_hit_to_dict(h) for h in rule_hits],
        summary={
            "model_finding_count": len(model_findings),
            "rule_hit_count": len(rule_hits),
            "needs_review_count": sum(
                1 for h in rule_hits if h.uncertainty.value in {"needs_review", "uncertain", "insufficient_data"}
            ),
        },
    )


def report_to_json(report: ReportArtifact) -> bytes:
    payload = asdict(report)
    payload["id"] = str(report.id)
    payload["document_id"] = str(report.document_id)
    payload["user_id"] = str(report.user_id)
    payload["analysis_run_id"] = str(report.analysis_run_id) if report.analysis_run_id else None
    payload["created_at"] = report.created_at.isoformat()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    assert_safe_message(text)
    return text.encode("utf-8")


def report_to_pdf_bytes(report: ReportArtifact) -> bytes:
    """Minimal PDF (no external deps) with disclaimer and counts — not a legal opinion."""
    lines = [
        "Docly — Analytic Report",
        f"Report-Version: {report.report_version}",
        f"Created: {report.created_at.isoformat()}",
        f"Document: {report.document_id}",
        "",
        "DISCLAIMER:",
        DISCLAIMER,
        "",
        f"Model findings: {report.summary['model_finding_count']}",
        f"Rule results: {report.summary['rule_hit_count']}",
        f"Needs review: {report.summary['needs_review_count']}",
        "",
        "Unanalyzed pages: " + (", ".join(str(p) for p in report.unanalyzed_pages) or "none"),
        "",
        "Sources:",
    ]
    for s in report.sources:
        lines.append(f"- {s.get('code')}: {s.get('title')}")
    lines.append("")
    lines.append("Rule results (severity = review priority):")
    for r in report.rule_results:
        lines.append(f"* [{r['severity']}/{r['result_kind']}] {r['rule_id']}: {r['message']}")
    lines.append("")
    lines.append("Model findings are listed separately from rule results.")

    # Escape for PDF literal strings
    content_lines = []
    y = 800
    content_lines.append("BT /F1 10 Tf")
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        # PDF Type1 Helvetica poorly handles Cyrillic; keep ASCII transliteration for built-in font
        ascii_line = safe.encode("ascii", "replace").decode("ascii")
        content_lines.append(f"1 0 0 1 40 {y} Tm ({ascii_line}) Tj")
        y -= 14
        if y < 40:
            break
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n",
    )
    objects.append(
        b"4 0 obj<< /Length " + str(len(stream)).encode() + b" >>stream\n" + stream + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(),
    )
    return bytes(out)
