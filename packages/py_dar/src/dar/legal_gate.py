from __future__ import annotations

"""Production legal package gate (shared)."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PLACEHOLDERS = (
    "OWNER_LEGAL_FORM",
    "OWNER_NAME",
    "INN",
    "OGRN_OR_OGRNIP",
    "ADDRESS",
    "SUPPORT_EMAIL",
    "PRIVACY_EMAIL",
    "PAYMENT_PROVIDER",
    "TARIFFS",
    "TRIAL",
    "RENEWAL",
    "REFUNDS",
    "RETENTION",
    "PROCESSORS",
    "DATA_LOCATIONS",
    "FINAL_CONSENT_MECHANISM_NEEDS_LEGAL_REVIEW",
    "LEGAL_BASIS_MATRIX_NEEDS_REVIEW",
    "PROCESSOR_DPA_NEEDS_REVIEW",
    "OWNER_LEGAL_NAME",
)


@dataclass
class LegalPackageReport:
    ok: bool
    errors: list[str]
    warnings: list[str]
    manifest: dict[str, Any] | None

    def raise_for_production(self) -> None:
        if not self.ok:
            raise RuntimeError("Legal package not production-ready: " + "; ".join(self.errors))


def load_manifest(legal_root: str | Path) -> dict[str, Any]:
    path = Path(legal_root) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _find_placeholders(text: str, tokens: list[str]) -> list[str]:
    found = []
    for tok in tokens:
        if re.search(rf"\b{re.escape(tok)}\b", text):
            found.append(tok)
    return found


def validate_legal_package(legal_root: str | Path, *, for_production: bool) -> LegalPackageReport:
    root = Path(legal_root)
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = load_manifest(root)
    except Exception as exc:  # noqa: BLE001
        return LegalPackageReport(False, [f"manifest missing/invalid: {exc}"], [], None)

    tokens = list(manifest.get("required_placeholders") or [])
    for extra in DEFAULT_PLACEHOLDERS:
        if extra not in tokens:
            tokens.append(extra)

    if for_production:
        if manifest.get("status") != "approved":
            errors.append("manifest.status must be 'approved' for production")
        approvals = manifest.get("approvals") or {}
        for role in ("lawyer", "privacy_officer"):
            st = (approvals.get(role) or {}).get("status")
            if st != "approved":
                errors.append(f"approvals.{role}.status must be approved (got {st!r})")
            if not (approvals.get(role) or {}).get("reviewer_id"):
                errors.append(f"approvals.{role}.reviewer_id required")

    docs = manifest.get("documents") or []
    if not docs:
        errors.append("manifest.documents empty")

    seen_ids: set[str] = set()
    for doc in docs:
        cid = str(doc.get("consent_id"))
        path = root / str(doc.get("path"))
        seen_ids.add(cid)
        if not path.is_file():
            errors.append(f"missing document file for {cid}: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if not doc.get("effective_version"):
            errors.append(f"{cid}: effective_version missing")
        if for_production and doc.get("publication_status") != "published":
            errors.append(f"{cid}: publication_status must be published for production")
        found = _find_placeholders(text, tokens)
        if for_production and found:
            errors.append(f"{cid}: unresolved placeholders: {', '.join(sorted(set(found)))}")
        elif found:
            warnings.append(f"{cid}: draft placeholders present: {', '.join(sorted(set(found)))}")
        if cid == "personal_data_processing" and doc.get("bundled_with"):
            errors.append("personal_data_processing must not be bundled with offer/terms")

    required_ids = {
        "offer",
        "terms_of_use",
        "privacy_policy",
        "personal_data_processing",
        "special_categories.medical",
        "cookies_notice",
        "marketing",
        "payment_recurring",
    }
    missing = required_ids - seen_ids
    if missing:
        errors.append(f"manifest missing documents: {sorted(missing)}")

    return LegalPackageReport(ok=len(errors) == 0, errors=errors, warnings=warnings, manifest=manifest)


def assert_legal_production_ready(legal_root: str | Path) -> None:
    validate_legal_package(legal_root, for_production=True).raise_for_production()
