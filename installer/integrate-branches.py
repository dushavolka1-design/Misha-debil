"""Merge pinned branch snapshots with reviewed documentation-only resolutions."""
import os
from pathlib import Path
import subprocess

BRANCHES = [
    ('master', '7ab48303efa92b2e52702256dcdd360c9540d273'),
    ('astra/docly-full-audit-20260906', '7ab48303efa92b2e52702256dcdd360c9540d273'),
    ('astra/docly-windows-installer-20260906', '7ab48303efa92b2e52702256dcdd360c9540d273'),
    ('backup-before-merge', 'd4e6da60507efb3f6aed78a1dd8ccd294e453386'),
    ('astra/docly-modern-redesign-20260906', 'db099db89d57a24a1255a545463cdd65e76c839c'),
    ('fix/docly-desktop-upgrade-safety', '59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d'),
    ('chore/docly-fast-windows-installer', '04372810841cf9839f1c97afec2b7690b3fa684b'),
]

def git(*args, check=True):
    result = subprocess.run(['git', *args], text=True, encoding='utf-8', errors='replace', capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def resolve_documentation(name, sha):
    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
    if conflicts != ['README.md']:
        return False
    original = git('show', sha + ':README.md').stdout
    archive = Path('docs/branch-history')
    archive.mkdir(parents=True, exist_ok=True)
    if name == 'backup-before-merge' and original == '# Misha-debil\n$\n':
        (archive / 'backup-before-merge.README.md').write_text(original, encoding='utf-8')
        git('checkout', '--ours', '--', 'README.md')
    elif name == 'fix/docly-desktop-upgrade-safety' and sha == '59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d':
        # Both files were inspected. Safety README corrects obsolete PostgreSQL desktop docs.
        # Preserve originals and explicitly distinguish this online installer from its offline alternative.
        current = git('show', 'HEAD:README.md').stdout
        (archive / 'pre-integration.README.md').write_text(current, encoding='utf-8')
        (archive / 'desktop-safety.README.md').write_text(original, encoding='utf-8')
        header = '''# Docly — объединённая Windows-версия

## Основная сборка этой ветки

Рабочая ветка: `release/docly-all-branches-20260908`, база PR: `master` (не `main`).
Объединены снимки всех запрошенных веток; точный состав и доказательство включения: [installer/INTEGRATION.md](installer/INTEGRATION.md).
Статус новой сборки: [installer/INTEGRATED-CI.md](installer/INTEGRATED-CI.md). Старый CI-RESULT.md относится к предыдущему EXE.

```powershell
git switch release/docly-all-branches-20260908
pnpm installer:windows
```

Результат: `release/Docly-Setup-x64.exe`. Сборка требует Windows x64 и Inno Setup 6.3+.
Этот быстрый установщик НЕ включает Node/Python и готовые зависимости: нужен интернет при первом запуске.
Используются существующий launcher, SQLite и файловое хранилище; PostgreSQL/Redis/Docker не нужны.
Установка для пользователя: `%LOCALAPPDATA%\\Programs\\Docly`. Проверки Node/Python, ярлыки и штатное удаление описаны в [installer/README.md](installer/README.md).
Пользовательские данные сохраняются. Не путайте этот EXE с альтернативным offline-установщиком из `scripts/windows` ниже.

Документация desktop-safety сохранена далее; её утверждения о встроенных runtime и offline-установке относятся ТОЛЬКО к альтернативной команде `scripts/windows/build-installer.ps1`, а не к `pnpm installer:windows`.
Ручная приёмка Windows 10/11 и production-ready статус не заявляются.

---

'''
        adjusted = original.replace('- Целевая основная ветка: `main`.', '- Историческая целевая ветка desktop-safety: `main`; для текущего объединения база PR — `master`.').replace('# После слияния PR используйте main.', '# Это альтернативная offline-сборка исходной desktop-safety ветки.').replace('## Windows: сборка из чистого клона', '## Альтернативная offline-сборка desktop-safety из чистого клона')
        Path('README.md').write_text(header + adjusted, encoding='utf-8')
    else:
        return False
    git('add', 'README.md', str(archive))
    git('commit', '--no-edit')
    return True


def main():
    branch = os.environ['GITHUB_REF_NAME']
    if branch != 'release/docly-all-branches-20260908':
        raise SystemExit('Integration is restricted to its dedicated branch')
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('checkout', branch)
    report = ['# All-branches integration evidence', '', 'main is not used as an input branch. Its current commit equals backup-before-merge; that shared history is necessarily included via the requested backup branch. Snapshots pinned on 2026-09-08.', '', '| Branch | Snapshot | Result |', '| --- | --- | --- |']
    try:
        for name, sha in BRANCHES:
            git('cat-file', '-e', sha + '^{commit}')
            if git('merge-base', '--is-ancestor', sha, 'HEAD', check=False).returncode == 0:
                outcome = 'Already included (ancestor of HEAD)'
            else:
                options = ['--allow-unrelated-histories'] if name == 'backup-before-merge' else []
                result = git('merge', '--no-ff', '--no-edit', *options, sha, '-m', f'Merge {name} into integrated Docly release', check=False)
                resolved = resolve_documentation(name, sha) if result.returncode else False
                if result.returncode and not resolved:
                    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout
                    report += [f'| {name} | {sha} | MERGE FAILED |', '', 'Unresolved conflicts (not discarded):', '```text', conflicts, result.stdout, result.stderr, '```']
                    git('merge', '--abort', check=False)
                    raise RuntimeError(f'Merge failed: {name}')
                outcome = 'Merged; reviewed README conflict resolved, originals in docs/branch-history' if resolved else 'Merged without conflicts'
            report.append(f'| {name} | {sha} | {outcome} |')
        for _, sha in BRANCHES:
            git('merge-base', '--is-ancestor', sha, 'HEAD')
        report += ['', 'All requested snapshot commits are ancestors of the integrated HEAD.', '', '## Net changes versus installer baseline', '```text', git('diff', '--stat', '04372810841cf9839f1c97afec2b7690b3fa684b', 'HEAD').stdout, '```', '', '## Changed paths', '```text', git('diff', '--name-status', '04372810841cf9839f1c97afec2b7690b3fa684b', 'HEAD').stdout, '```']
    finally:
        Path('installer/INTEGRATION.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
        git('add', 'installer/INTEGRATION.md')
        if git('diff', '--cached', '--quiet', check=False).returncode != 0:
            git('commit', '-m', 'docs: record branch integration evidence [skip ci]')
        git('push', 'origin', 'HEAD:refs/heads/' + branch)
    sha = git('rev-parse', 'HEAD').stdout.strip()
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write('sha=' + sha + '\n')
    print('Integrated source:', sha)

if __name__ == '__main__':
    main()
