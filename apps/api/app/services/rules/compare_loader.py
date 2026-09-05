from __future__ import annotations

from typing import Any
from uuid import UUID

from app.services.analysis.pipeline import AnalysisRunRecord
from app.services.rules.compare import CompareDoc


def _finding_to_party(f: dict[str, Any]) -> dict[str, Any] | None:
    et = str(f.get("entity_type", ""))
    if not et.startswith("party"):
        return None
    return {
        "name": f.get("raw_text", ""),
        "role": et.replace("party.", ""),
        "citation": f.get("citation"),
    }


def _finding_to_clause(f: dict[str, Any]) -> dict[str, Any]:
    et = str(f.get("entity_type", ""))
    return {
        "key": et,
        "text": f.get("raw_text", ""),
        "citation": f.get("citation"),
    }


def build_compare_doc_from_run(
    *,
    document_id: UUID,
    user_id: UUID,
    tenant_id: UUID,
    display_name: str,
    run: AnalysisRunRecord,
) -> CompareDoc:
    findings = [
        {
            "entity_type": f.entity_type,
            "raw_text": f.raw_text,
            "normalized_value": f.normalized_value,
            "citation": f.citation,
            "kind": f.kind,
        }
        for f in run.findings
        if f.entity_type != "analysis.capability"
    ]
    parties: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    clauses: list[dict[str, Any]] = []
    title = display_name

    for f in findings:
        et = f["entity_type"]
        if et == "doc.title":
            title = str(f.get("raw_text") or title)
            sections.append({"path": "title", "text": f.get("raw_text", ""), "citation": f.get("citation")})
            continue
        party = _finding_to_party(f)
        if party:
            parties.append(party)
            continue
        clauses.append(_finding_to_clause(f))

    return CompareDoc(
        document_id=document_id,
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        sections=sections,
        parties=parties,
        clauses=clauses,
    )
