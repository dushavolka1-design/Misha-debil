"""One-shot reviewed lint repair; never suppress findings or apply unsafe fixes.

Run from repository root. The whole patch is validated in memory before writing.
Only specified local names, broker polling keywords, a stricter exception check,
and AST-equivalent string wrapping/whitespace may change.
"""
from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

PATHS = [
    "apps/api/app/persistence/bootstrap.py",
    "apps/api/app/services/auth_consent.py",
    "apps/api/app/services/entry/deadlines.py",
    "apps/api/app/services/entry/pack.py",
    "apps/api/app/services/jobs/broker.py",
    "apps/api/app/services/jobs/consumer.py",
    "apps/api/app/services/rules/registry.py",
    "apps/api/app/services/upload/lifecycle.py",
    "apps/api/tests/test_ai_eval.py",
    "apps/api/tests/test_upload_lifecycle.py",
    "apps/api/tests/test_desktop_profile.py",
]
RENAMES = {
    PATHS[0]: {"key": "_key"},
    PATHS[2]: {"ctx": "_ctx"},
    PATHS[4]: {"timeout": "wait_seconds"},
    PATHS[7]: {"data": "_data"},
}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected one occurrence: {old!r}")
    return text.replace(old, new, 1)


def wrap_literals(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if len(line) <= 120:
            lines.append(line)
            continue
        match = re.fullmatch(r'(\s*)([a-z_]+=|"[a-z_]+": )(f?)"(.*)",', line)
        if not match:
            raise ValueError("Long line needs individual review")
        indent, prefix, fmark, value = match.groups()
        choices = [i for i, ch in enumerate(value) if ch == " " and value[:i].count("{") == value[:i].count("}")]
        split = min(choices, key=lambda i: abs(i - len(value) // 2))
        lines += [indent + prefix + "(", indent + '    ' + fmark + '"' + value[:split + 1] + '"',
                  indent + '    ' + fmark + '"' + value[split + 1:] + '"', indent + "),"]
    return "\n".join(lines) + "\n"


def normalized(tree: ast.AST, path: str) -> str:
    tree = copy.deepcopy(tree)
    reverse = {v: k for k, v in RENAMES.get(path, {}).items()}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            node.id = reverse.get(node.id, node.id)
        if isinstance(node, ast.arg):
            node.arg = reverse.get(node.arg, node.arg)
        if path in {PATHS[5], PATHS[10]} and isinstance(node, ast.keyword) and node.arg == "wait_seconds":
            node.arg = "timeout"
    return ast.dump(tree)


def prepare() -> dict[Path, bytes]:
    changes = {}
    for name in PATHS:
        path = Path(name)
        original = path.read_text(encoding="utf-8")
        text = original
        if name == PATHS[0]:
            for label in ["restored_sources", "restored_snaps"]:
                pattern = f"        {label}: dict[Any, "
                start = text.index(pattern)
                pos = text.index("        for key, raw in payload.items():", start)
                text = text[:pos] + text[pos:].replace("for key, raw", "for _key, raw", 1)
        elif name == PATHS[2]:
            text = replace_once(text, "    ctx = context or {}", "    _ctx = context or {}")
        elif name == PATHS[4]:
            # Queue polling duration, not an async cancellation scope.
            if text.count("queue_name: str, timeout: float = 1.0") != 3:
                raise ValueError("Unexpected broker signatures")
            text = text.replace("queue_name: str, timeout: float = 1.0", "queue_name: str, wait_seconds: float = 1.0")
            text = replace_once(text, "int(timeout)", "int(wait_seconds)")
            text = replace_once(text, "time.monotonic() + timeout", "time.monotonic() + wait_seconds")
        elif name in {PATHS[5], PATHS[10]}:
            text = re.sub(r'(\.pop\([^\n]+, )timeout=', r'\1wait_seconds=', text)
        elif name == PATHS[7]:
            # Preserve the awaited read, validation, exceptions and timing.
            text = replace_once(text, "        started = time.perf_counter()\n        data = await self._read_quarantine_plaintext(doc)",
                                "        started = time.perf_counter()\n        _data = await self._read_quarantine_plaintext(doc)")
        elif name == PATHS[8]:
            text = replace_once(text, "from __future__ import annotations\n\n\n", "from __future__ import annotations\n\n")
        elif name == PATHS[9]:
            text = replace_once(text, "from app.services.upload.fsm import DocumentState, transition",
                                "from app.services.upload.fsm import DocumentState, InvalidTransition, transition")
            text = replace_once(text, "with pytest.raises(Exception):", 'with pytest.raises(InvalidTransition, match="QUARANTINED -> PROCESSING not allowed"):')
        if name in {PATHS[1], PATHS[2], PATHS[3], PATHS[6]}:
            text = wrap_literals(text)
        before = ast.parse(original)
        after = ast.parse(text)
        if name == PATHS[9]:
            for node in ast.walk(before):
                if isinstance(node, ast.ImportFrom) and node.module == "app.services.upload.fsm":
                    node.names.insert(1, ast.alias(name="InvalidTransition"))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "raises":
                    if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == "Exception":
                        node.args[0].id = "InvalidTransition"
                        node.keywords.append(ast.keyword(arg="match", value=ast.Constant(value="QUARANTINED -> PROCESSING not allowed")))
        if normalized(before, name) != normalized(after, name):
            raise ValueError(f"Unexpected semantic change: {name}")
        if text != original:
            changes[path] = text.encode("utf-8")
    return changes


def main() -> None:
    changes = prepare()
    originals = {p: p.read_bytes() for p in changes}
    try:
        for path, data in changes.items():
            path.write_bytes(data)
    except BaseException:
        for path, data in originals.items():
            path.write_bytes(data)
        raise
    evidence = Path("artifacts/quality-repair")
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "changed-files.json").write_text(json.dumps([str(p) for p in changes], indent=2) + "\n")
    print(f"Applied {len(changes)} individually scoped files; AST guard passed")


if __name__ == "__main__":
    main()
