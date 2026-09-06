"""Document comparison with ownership isolation and dual citations."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


class CompareError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


@dataclass
class CompareDoc:
    document_id: UUID
    user_id: UUID
    tenant_id: UUID
    title: str
    sections: list[dict[str, Any]]  # {path, text, citation}
    parties: list[dict[str, Any]]
    clauses: list[dict[str, Any]]  # semantic clauses


@dataclass
class DiffItem:
    change: str  # added|removed|changed
    path: str
    left_citation: dict[str, Any] | None
    right_citation: dict[str, Any] | None
    left_text: str | None
    right_text: str | None


@dataclass
class CompareResult:
    left_document_id: UUID
    right_document_id: UUID
    user_id: UUID
    tenant_id: UUID
    party_diffs: list[DiffItem] = field(default_factory=list)
    section_diffs: list[DiffItem] = field(default_factory=list)
    clause_diffs: list[DiffItem] = field(default_factory=list)
    model_notes: list[str] = field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None


_INJECTION = re.compile(r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions|exfiltrat|other user|leak")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _fingerprint(user_id: UUID, tenant_id: UUID, doc_id: UUID) -> str:
    return hashlib.sha256(f"{tenant_id}:{user_id}:{doc_id}".encode()).hexdigest()[:16]


def compare_documents(left: CompareDoc, right: CompareDoc) -> CompareResult:
    if left.user_id != right.user_id or left.tenant_id != right.tenant_id:
        raise CompareError("cross_user_forbidden", "Comparison across users/tenants is forbidden", http_status=403)

    # Prompt-injection / context-mixing guard on clause texts before any LLM-like step
    for doc in (left, right):
        blob = " ".join(c.get("text", "") for c in doc.clauses + doc.sections)
        if _INJECTION.search(blob):
            return CompareResult(
                left_document_id=left.document_id,
                right_document_id=right.document_id,
                user_id=left.user_id,
                tenant_id=left.tenant_id,
                refused=True,
                refusal_reason="prompt_injection_refused",
            )

    # Bind context fingerprints so comparator never mixes foreign docs
    _ = (
        _fingerprint(left.user_id, left.tenant_id, left.document_id),
        _fingerprint(right.user_id, right.tenant_id, right.document_id),
    )

    result = CompareResult(
        left_document_id=left.document_id,
        right_document_id=right.document_id,
        user_id=left.user_id,
        tenant_id=left.tenant_id,
    )

    # Parties
    lp = {_norm(p.get("name", "")): p for p in left.parties if p.get("name")}
    rp = {_norm(p.get("name", "")): p for p in right.parties if p.get("name")}
    for k in sorted(set(lp) | set(rp)):
        if k in lp and k not in rp:
            result.party_diffs.append(
                DiffItem("removed", f"party:{k}", lp[k].get("citation"), None, lp[k].get("name"), None),
            )
        elif k not in lp and k in rp:
            result.party_diffs.append(
                DiffItem("added", f"party:{k}", None, rp[k].get("citation"), None, rp[k].get("name")),
            )
        elif lp[k].get("role") != rp[k].get("role"):
            result.party_diffs.append(
                DiffItem(
                    "changed",
                    f"party:{k}.role",
                    lp[k].get("citation"),
                    rp[k].get("citation"),
                    str(lp[k].get("role")),
                    str(rp[k].get("role")),
                ),
            )

    # Section hierarchy
    ls = {_norm(s.get("path", "")): s for s in left.sections}
    rs = {_norm(s.get("path", "")): s for s in right.sections}
    for path in sorted(set(ls) | set(rs)):
        if path in ls and path not in rs:
            result.section_diffs.append(
                DiffItem("removed", path, ls[path].get("citation"), None, ls[path].get("text"), None),
            )
        elif path not in ls and path in rs:
            result.section_diffs.append(
                DiffItem("added", path, None, rs[path].get("citation"), None, rs[path].get("text")),
            )
        elif _norm(ls[path].get("text", "")) != _norm(rs[path].get("text", "")):
            result.section_diffs.append(
                DiffItem(
                    "changed",
                    path,
                    ls[path].get("citation"),
                    rs[path].get("citation"),
                    ls[path].get("text"),
                    rs[path].get("text"),
                ),
            )

    # Semantic clauses
    lc = {_norm(c.get("key", c.get("text", ""))): c for c in left.clauses}
    rc = {_norm(c.get("key", c.get("text", ""))): c for c in right.clauses}
    for key in sorted(set(lc) | set(rc)):
        if key in lc and key not in rc:
            result.clause_diffs.append(
                DiffItem("removed", f"clause:{key}", lc[key].get("citation"), None, lc[key].get("text"), None),
            )
        elif key not in lc and key in rc:
            result.clause_diffs.append(
                DiffItem("added", f"clause:{key}", None, rc[key].get("citation"), None, rc[key].get("text")),
            )
        elif _norm(lc[key].get("text", "")) != _norm(rc[key].get("text", "")):
            result.clause_diffs.append(
                DiffItem(
                    "changed",
                    f"clause:{key}",
                    lc[key].get("citation"),
                    rc[key].get("citation"),
                    lc[key].get("text"),
                    rc[key].get("text"),
                ),
            )

    result.model_notes.append("deterministic_diff_v1")
    return result
