"""Inventory every tracked blob at every branch/tag tip without executing content.

Candidates are NOT verified forms. A complete file index is retained so heuristic
false negatives can be reviewed. No raw document contents are copied to reports.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], timeout=60)


def inventory() -> dict:
    if git("rev-parse", "--is-shallow-repository").strip() != b"false":
        raise RuntimeError("Full history is required")
    refs = git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes/origin", "refs/tags").decode().splitlines()
    refs = [ref for ref in refs if not ref.endswith("/HEAD")]
    if not refs:
        raise RuntimeError("No branch or tag refs found")
    extensions = {".pdf", ".doc", ".docx", ".odt", ".xlsx", ".xls", ".html", ".htm", ".json", ".yaml", ".yml", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"}
    marker = re.compile(r"template|schema|snapshot|fixture|forms?|worksheet|pixel|бланк|шаблон|приказ.{0,60}мвд|publication\.pravo\.gov\.ru", re.I)
    cached = {}
    files = []
    resolved = {}
    for ref in sorted(refs):
        commit = git("rev-parse", ref + "^{commit}").decode().strip()
        resolved[ref] = commit
        for raw in git("ls-tree", "-r", "-z", commit).split(b"\0"):
            if not raw:
                continue
            header, name = raw.split(b"\t", 1)
            mode, kind, blob = header.decode().split()
            path = name.decode("utf-8", "surrogateescape")
            if kind != "blob":
                files.append({"ref": ref, "commit": commit, "path": path, "kind": kind, "object": blob, "status": "external_object_not_inspected"})
                continue
            if blob not in cached:
                data = git("cat-file", "blob", blob)
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = ""
                cached[blob] = (hashlib.sha256(data).hexdigest(), len(data), bool(marker.search(text)))
            digest, size, content_match = cached[blob]
            candidate = Path(path).suffix.lower() in extensions or bool(marker.search(path)) or content_match
            files.append({
                "ref": ref, "commit": commit, "path": path, "git_blob": blob,
                "sha256": digest, "size": size, "mode": mode,
                "candidate": candidate, "format": Path(path).suffix.lower() or "source",
                "status": "needs_classification_and_official_verification" if candidate else "indexed_not_classified",
            })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auditor_commit": git("rev-parse", "HEAD").decode().strip(),
        "scope": "all fetched branch and tag tips; full file index, heuristic candidate classification",
        "official_verification": "not_performed_by_inventory",
        "pixel_diff": "not_performed_by_inventory",
        "refs": resolved, "files": files,
    }


if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/template-audit/inventory.json")
    result = inventory()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"refs": result["refs"], "indexed_entries": len(result["files"]), "candidate_entries": sum(bool(row.get("candidate")) for row in result["files"])}))
