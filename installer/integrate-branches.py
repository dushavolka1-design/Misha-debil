"""Merge the user-requested branch snapshots, never main or force-selected conflicts."""
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


def main():
    branch = os.environ['GITHUB_REF_NAME']
    if branch != 'release/docly-all-branches-20260908':
        raise SystemExit('Integration is restricted to its dedicated branch')
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('checkout', branch)
    baseline = git('rev-parse', 'HEAD').stdout.strip()
    report = ['# All-branches integration evidence', '', 'main is excluded. Branch snapshots are pinned to the requested integration on 2026-09-08.', '', '| Branch | Snapshot | Result |', '| --- | --- | --- |']
    try:
        for name, sha in BRANCHES:
            git('cat-file', '-e', sha + '^{commit}')
            if git('merge-base', '--is-ancestor', sha, 'HEAD', check=False).returncode == 0:
                outcome = 'Already included (ancestor of HEAD)'
            else:
                result = git('merge', '--no-ff', '--no-edit', sha, '-m', f'Merge {name} into integrated Docly release', check=False)
                if result.returncode:
                    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout
                    report += [f'| {name} | {sha} | MERGE FAILED |', '', 'Conflicts (no automatic ours/theirs resolution):', '```text', conflicts, result.stdout, result.stderr, '```']
                    git('merge', '--abort', check=False)
                    raise RuntimeError(f'Merge failed: {name}')
                outcome = 'Merged without conflicts'
            report.append(f'| {name} | {sha} | {outcome} |')
        for _, sha in BRANCHES:
            git('merge-base', '--is-ancestor', sha, 'HEAD')
        report += ['', 'All requested snapshot commits are ancestors of the integrated HEAD.', '', '## Net changes versus installer baseline', '```text', git('diff', '--stat', baseline, 'HEAD').stdout, '```', '', '## Changed paths', '```text', git('diff', '--name-status', baseline, 'HEAD').stdout, '```']
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
