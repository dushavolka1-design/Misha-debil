"""Apply safe unused-import fixes with an independent AST scope guard.

Only allowlisted standard-library imports may disappear completely.
Other imports must retain a member and their position. All other AST nodes
must remain unchanged. This is not permission to apply unsafe Ruff fixes.
"""
from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOTS = ['apps/api/app', 'apps/api/tests', 'packages/py_dar/src']
REMOVABLE_MODULES = {'datetime', 'dataclasses', 'typing', 'pathlib', 'json', 'hmac', 'os'}


def normalized_original(before: ast.AST, after: ast.AST) -> ast.AST:
    original = copy.deepcopy(before)
    remaining = [n for n in ast.walk(after) if isinstance(n, (ast.Import, ast.ImportFrom))]

    class Guard(ast.NodeTransformer):
        def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | None:
            key = (node.module, node.level)
            candidate = next((n for n in remaining if isinstance(n, ast.ImportFrom)
                              and (n.module, n.level) == key
                              and all(ast.dump(a) in {ast.dump(x) for x in node.names} for a in n.names)), None)
            if candidate is not None:
                remaining.remove(candidate)
                node.names = copy.deepcopy(candidate.names)
                return node
            if node.level != 0 or node.module not in REMOVABLE_MODULES:
                raise RuntimeError(f'Refusing removal of import from {node.module}')
            return None

        def visit_Import(self, node: ast.Import) -> ast.AST | None:
            candidate = next((n for n in remaining if isinstance(n, ast.Import)
                              and all(ast.dump(a) in {ast.dump(x) for x in node.names} for a in n.names)), None)
            if candidate is not None:
                removed = {a.name for a in node.names} - {a.name for a in candidate.names}
                if not removed <= REMOVABLE_MODULES:
                    raise RuntimeError(f'Refusing removal of modules: {removed}')
                remaining.remove(candidate)
                node.names = copy.deepcopy(candidate.names)
                return node
            if not {a.name for a in node.names} <= REMOVABLE_MODULES:
                raise RuntimeError('Refusing removal of non-allowlisted module import')
            return None

    result = Guard().visit(original)
    if remaining or ast.dump(result) != ast.dump(after):
        raise RuntimeError('Non-import behavior or import position changed')
    return result


def main() -> None:
    paths = [p for root in ROOTS for p in Path(root).rglob('*.py')]
    originals = {p: p.read_bytes() for p in paths}
    evidence = Path('artifacts/import-cleanup')
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([sys.executable, '-m', 'ruff', 'check', '--select', 'F401',
                        '--fix', '--no-unsafe-fixes', *ROOTS], check=True)
        changed = []
        for path, raw in originals.items():
            current = path.read_bytes()
            if current == raw:
                continue
            if path.name == '__init__.py':
                raise RuntimeError(f'Review public re-exports manually: {path}')
            normalized_original(ast.parse(raw), ast.parse(current))
            changed.append(str(path))
        (evidence / 'changed-files.json').write_text(json.dumps(changed, indent=2) + '\n')
        print(f'AST guard passed for {len(changed)} files; only reviewed import removals')
    except BaseException:
        for path, raw in originals.items():
            path.write_bytes(raw)
        raise


if __name__ == '__main__':
    main()
