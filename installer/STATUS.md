# Docly Windows installer — continuation checkpoint

## Baseline / scope
- Repo: dushavolka1-design/Misha-debil.
- Working branch: `chore/docly-fast-windows-installer`, created from master `7ab48303efa92b2e52702256dcdd360c9540d273`.
- astra/docly-windows-installer-20260906 has the same baseline SHA.
- fix/docly-desktop-upgrade-safety was inspected at `59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d`; no unrelated changes imported.
- Current master desktop launcher uses SQLite/file storage, not PostgreSQL/Redis/Alembic. This is intentionally preserved. No product API/UI/schema/analysis changes.
- Draft PR: https://github.com/dushavolka1-design/Misha-debil/pull/2 (base master). No merge performed.

## Implemented
- Inno Setup config, per-user installation to LOCALAPPDATA/Programs/Docly, desktop and Start Menu shortcuts, installed-programs registration and uninstaller.
- Filtered tracked-source payload with secret/cache/data exclusions, SHA256 and size metadata.
- Russian dependency checks, optional winget, official-site fallback.
- First-run wrapper: local .env/random session secret, venv, existing Python requirements, pnpm 9.15.9, frozen JS dependencies, production Next build, original font/icon scripts, original VBS/launcher.
- Windows Actions compile and smoke. Prerelease publication is gated on passing smoke. Failure artifacts are NOT releases.
- CI result and diagnostics persisted in installer/CI-RESULT.md and installer/DIAGNOSTICS.md.

## Latest work (2026-09-08, before release confirmation)
- Last fully inspected build: `cc539e25d14c48f0896756d8b2711f7df29cba8a`; EXE built (3,052,350 bytes).
- Installation, both shortcuts, registration, absence of .env/venv/node_modules in shipped payload passed.
- Full Python/JS dependency installation and Next production compilation/typechecking passed.
- API startup failed because the payload lacked `sources/allowlist.json`.
- FIX committed at `47873cda75018ebc3c58bb78f138ce60e06308e4`: package that exact non-secret runtime config and require it during staging. A new Windows run was triggered; result not yet confirmed at this checkpoint.
- Earlier fixed installer-only problems: Windows PowerShell native argument quoting, uninstaller included in running-process detection, upload UI source wrongly excluded by data filter.
- Local JSON/YAML parsing and payload filter regression checks passed. Windows PowerShell syntax and Inno compilation passed in real CI.

## Resume here
1. Read installer/CI-RESULT.md and compare its Source commit with the latest implementation commit above (or any newer fix). Do not confuse old results with the latest run.
2. Read actual Windows logs for any remaining installer/launcher blocker. installer-diagnostics.yml can retrieve job status/log excerpts; CI-RESULT includes API error tails.
3. Wait for install -> first launch -> /live -> /ready -> /app/analyzer -> second launch -> stop -> reinstall preservation -> standard uninstall to pass.
4. Verify GitHub prerelease and its EXE asset/size/SHA256. Only then report completion, update this checkpoint and PR.
5. Do NOT claim manual Windows 10/11 GUI/winget tests passed; they have not been run. CI uses Windows Server 2022 and headless launcher. Existing unrelated monorepo JS/Python/security checks also fail; no unrelated fixes should be added.

## Environment / commands
Assistant sandbox is Linux, without Windows/Inno/PowerShell, direct github.com DNS or a user browser. GitHub connector read/write works; Windows execution is via GitHub Actions.
Rebuild on Windows: `pnpm installer:windows` (Inno Setup 6.3+ and Git required).
Expected output: `release/Docly-Setup-x64.exe`. Binary is distributed as a release asset / CI artifact, not committed into Git source history.
Use `[skip ci]` for checkpoint-only commits to avoid needless rebuilds.

## Known first-version limitations
Internet required on first run. No code signature, no updater, no bundled Node/Python. Python packages retain original version ranges. User data, .env and logs intentionally survive uninstall. Existing runtime processes must be closed before install/uninstall; no unsafe blanket process killing.
