"""Prove scanner coverage of two deleted roots and a deleted merge-only file.

The fixture contains synthetic markers, never credentials. This does not replace
scanning the actual repository. A missing detection or scanner failure is fatal.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

LOG_OPTIONS = "--all --full-history --root -m"


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def build_fixture(root: Path) -> dict[str, str]:
    root.mkdir()
    git(root, "init", "--initial-branch=first")
    git(root, "config", "user.name", "Synthetic history test")
    git(root, "config", "user.email", "history-test@example.invalid")
    expected = {}
    for branch, name, marker in [
        ("first", "first.txt", "ROOT_ONE"),
        ("second", "second.txt", "ROOT_TWO"),
    ]:
        if branch == "second":
            git(root, "checkout", "--orphan", branch)
        (root / name).write_text("DOCLY_HISTORY_FIXTURE_" + marker + "\n", encoding="utf-8")
        git(root, "add", name)
        git(root, "commit", "-m", "Synthetic independent root")
        expected[name] = git(root, "rev-parse", "HEAD")
        git(root, "rm", name)
        git(root, "commit", "-m", "Remove synthetic root marker")
    git(root, "merge", "--allow-unrelated-histories", "--no-ff", "--no-commit", "first")
    (root / "merge.txt").write_text("DOCLY_HISTORY_FIXTURE_" + "MERGE_ONLY\n", encoding="utf-8")
    git(root, "add", "merge.txt")
    git(root, "commit", "-m", "Synthetic merge-only content")
    expected["merge.txt"] = git(root, "rev-parse", "HEAD")
    git(root, "rm", "merge.txt")
    git(root, "commit", "-m", "Remove synthetic merge marker")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gitleaks", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    scanner = args.gitleaks.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        expected = build_fixture(root / "repo")
        config = root / "fixture.toml"
        config.write_text(
            'title = "Synthetic history coverage"\n[[rules]]\nid = "history-fixture"\n'
            'description = "Synthetic marker only"\n'
            "regex = '''DOCLY_HISTORY_FIXTURE_[A-Z_]+'''\n",
            encoding="utf-8",
        )
        report = root / "findings.json"
        command = [
            str(scanner), "git", "--redact", "--exit-code", "1", "--config", str(config),
            "--log-opts=" + LOG_OPTIONS, "--report-format", "json", "--report-path", str(report),
            str(root / "repo"),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (args.output / "fixture-scanner.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode != 1 or not report.is_file():
            raise RuntimeError("Scanner must detect all synthetic historical markers and return exactly 1")
        findings = json.loads(report.read_text(encoding="utf-8"))
        actual = {(item["File"], item["Commit"]) for item in findings}
        if actual != set(expected.items()):
            raise RuntimeError(f"Historical coverage mismatch: expected {expected!r}, received {actual!r}")
        evidence = {
            "log_options": LOG_OPTIONS, "expected": expected, "detections": findings,
            "scanner_version": subprocess.run(
                [str(scanner), "version"], check=True, capture_output=True, text=True
            ).stdout.strip(),
        }
        (args.output / "fixture-result.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print("PASS: actual scanner detected both deleted roots and deleted merge-only content")


if __name__ == "__main__":
    main()
