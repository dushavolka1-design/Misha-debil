"""Stage relocatable Windows runtimes; never read developer data or .env files."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def main() -> None:
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 12):
        raise SystemExit('Build with Windows x64 CPython 3.12')
    stage = Path(sys.argv[1]).resolve()
    if not (stage / 'apps/web/.next/BUILD_ID').is_file():
        raise SystemExit('Missing production web build')
    runtime = stage / 'runtime'
    runtime.mkdir()
    python = runtime / 'python'
    python.mkdir()
    base = Path(sys.base_prefix)
    for name in ('python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll', 'LICENSE.txt'):
        shutil.copy2(base / name, python / name)
    for dll in base.glob('vcruntime*.dll'):
        shutil.copy2(dll, python / dll.name)
    for name in ('DLLs', 'Lib', 'tcl'):
        shutil.copytree(base / name, python / name,
                        ignore=shutil.ignore_patterns('site-packages', '__pycache__'))
    node = Path(shutil.which('node') or '')
    if not node.is_file():
        raise SystemExit('Node executable missing')
    (runtime / 'node').mkdir()
    shutil.copy2(node, runtime / 'node/node.exe')
    shutil.copy2(node.parent / 'LICENSE', runtime / 'node/LICENSE')

    # Inno does not preserve pnpm junctions. Materialize workspace links using
    # the hoisted dependency layout, while refusing links outside this payload.
    for _ in range(10):
        links = []
        for directory, dirs, files in os.walk(stage, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink() or path.is_junction():
                    links.append(path)
        if not links:
            break
        for link in links:
            target = link.resolve(strict=True)
            if not target.is_relative_to(stage):
                raise RuntimeError(f'External link refused: {link}')
            temporary = link.with_name(link.name + '.materialized')
            if target.is_dir():
                relative = target.relative_to(stage)
                workspace = relative.parts[0] in {'apps', 'packages'}
                ignore = shutil.ignore_patterns('node_modules', '.next', '.venv') if workspace else None
                shutil.copytree(target, temporary, symlinks=True, ignore=ignore)
            else:
                shutil.copy2(target, temporary)
            if link.is_junction():
                link.rmdir()
            else:
                link.unlink()
            temporary.rename(link)
    else:
        raise RuntimeError('Unresolved/cyclic dependency links')
    for path in stage.rglob('.env'):
        raise RuntimeError(f'Real environment file must not be packaged: {path}')
    (stage / 'version.json').write_text(json.dumps({
        'version': sys.argv[2], 'source_commit': sys.argv[3],
        'python': sys.version.split()[0], 'platform': 'windows-x64',
    }, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
