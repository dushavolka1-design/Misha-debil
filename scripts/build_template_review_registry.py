"""Archive indexed template candidates without claiming official acceptance.

Input comes from audit_template_inventory.py. Contents are never executed and
archive names are content hashes, not potentially unsafe repository paths.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024


def classify(path: str, mode: str) -> str:
    if mode == "120000":
        return "symlink_not_a_verified_document"
    suffix = Path(path).suffix.lower()
    if suffix in {".pdf", ".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx"}:
        return "document_candidate_not_verified"
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"}:
        return "image_or_drawing_candidate"
    if suffix in {".json", ".yaml", ".yml"}:
        return "structured_data_or_configuration"
    return "source_code_or_documentation"


def build_registry(inventory: dict[str, Any], output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Output must be new; existing evidence is never overwritten")
    refs = inventory.get("refs")
    files = inventory.get("files")
    if not isinstance(refs, dict) or not refs or not isinstance(files, list):
        raise ValueError("Missing all-ref inventory")
    for ref, commit in refs.items():
        if not isinstance(ref, str) or not isinstance(commit, str) or not HEX40.fullmatch(commit):
            raise ValueError("Invalid ref identity")
    variants: dict[tuple[str, str], dict[str, Any]] = {}
    indexed_counts = {ref: 0 for ref in refs}
    candidate_counts = {ref: 0 for ref in refs}
    external_objects: list[dict[str, Any]] = []
    archive_blobs: dict[str, str] = {}
    resolved_origins: dict[tuple[str, str], str] = {}
    for row in files:
        if not isinstance(row, dict):
            raise ValueError("Invalid inventory entry")
        ref, commit, path = row.get("ref"), row.get("commit"), row.get("path")
        if ref not in refs or commit != refs[ref] or not isinstance(path, str):
            raise ValueError("Entry does not match the recorded ref")
        indexed_counts[ref] += 1
        if row.get("kind") is not None:
            external_objects.append(dict(row))
            continue
        if row.get("candidate") is not True:
            continue
        candidate_counts[ref] += 1
        digest, blob, size = row.get("sha256"), row.get("git_blob"), row.get("size")
        mode = row.get("mode")
        if (
            not isinstance(digest, str) or not HEX64.fullmatch(digest)
            or not isinstance(blob, str) or not HEX40.fullmatch(blob)
            or not isinstance(size, int) or isinstance(size, bool) or size < 0
            or mode not in {"100644", "100755", "120000"}
        ):
            raise ValueError("Invalid candidate identity")
        origin = (commit, path)
        if origin not in resolved_origins:
            resolved_origins[origin] = subprocess.check_output(
                ["git", "rev-parse", "--verify", f"{commit}:{path}"], timeout=60
            ).decode().strip()
        if resolved_origins[origin] != blob:
            raise ValueError("Candidate blob does not belong to recorded commit/path")
        key = (path, digest)
        if key not in variants:
            variants[key] = {
                "path": path,
                "sha256": digest,
                "size_bytes": size,
                "classification": classify(path, mode),
                "archive_blob": f"blobs/{digest}",
                "origins": [],
                "official_source_url": None,
                "order_number": None,
                "order_date": None,
                "effective_from": None,
                "effective_to": None,
                "official_pdf_sha256": None,
                "supersedes": None,
                "legal_acceptance": False,
                "pixel_acceptance": False,
                "review_status": "UNVERIFIED_NOT_FOR_OFFICIAL_SUBMISSION",
            }
        elif variants[key]["size_bytes"] != size:
            raise ValueError("Conflicting size for identical content")
        variants[key]["origins"].append({"ref": ref, "commit": commit, "git_blob": blob, "mode": mode})
        if digest in archive_blobs and archive_blobs[digest] != blob:
            raise ValueError("Conflicting Git identity for identical content")
        archive_blobs[digest] = blob
    if any(count == 0 for count in indexed_counts.values()):
        raise ValueError("A listed ref has no indexed entries")
    if not variants:
        raise ValueError("No candidates; not a complete template review registry")
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "blobs").mkdir()
        total_bytes = 0
        for digest, blob in sorted(archive_blobs.items()):
            size = int(subprocess.check_output(["git", "cat-file", "-s", blob], timeout=60))
            total_bytes += size
            if total_bytes > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive exceeds bounded size; review required")
            data = subprocess.check_output(["git", "cat-file", "blob", blob], timeout=60)
            if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("Candidate content hash verification failed")
            expected_sizes = {record["size_bytes"] for (_, sha), record in variants.items() if sha == digest}
            if expected_sizes != {size}:
                raise ValueError("Inventory size does not match actual Git blob")
            (output / "blobs" / digest).write_bytes(data)
        result = {
            "format": 1,
            "auditor_commit": inventory.get("auditor_commit"),
            "inventory_generated_at": inventory.get("generated_at"),
            "scope": "all indexed fetched branch and tag tips; heuristic candidates only",
            "acceptance": "NO_GO_REQUIRES_PER_FORM_OFFICIAL_AND_PIXEL_REVIEW",
            "archive_scope": "content-addressed copies of indexed candidates, including old branch-tip variants; not all historical revisions",
            "refs": refs,
            "indexed_entries_by_ref": indexed_counts,
            "candidate_entries_by_ref": candidate_counts,
            "external_objects_not_inspected": external_objects,
            "unique_archived_blobs": len(archive_blobs),
            "archive_bytes": total_bytes,
            "records": [variants[key] for key in sorted(variants)],
        }
        (output / "registry.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        (output / "README.txt").write_text(
            "NOT ACCEPTED FOR OFFICIAL SUBMISSION\n"
            "Classification is heuristic. No order, effective date or official source is inferred.\n"
            "Blobs are original Git bytes, named by verified SHA-256, never executed.\n"
            "Symlink blobs contain link text only; links were not followed.\n"
            "Branch-tip archives do not establish complete historical revision coverage.\n"
            "Read registry.json origins to identify each source ref/commit/path.\n",
            encoding="utf-8",
        )
        return result
    except BaseException:
        # This is a newly created evidence directory, never a user profile.
        shutil.rmtree(output)
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: build_template_review_registry.py INVENTORY_JSON NEW_OUTPUT_DIRECTORY")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = build_registry(data, Path(sys.argv[2]))
    print(json.dumps({"records": len(result["records"]), "blobs": result["unique_archived_blobs"], "bytes": result["archive_bytes"], "acceptance": result["acceptance"]}))
