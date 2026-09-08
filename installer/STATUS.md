# Docly Windows installer — released checkpoint

## Result, 2026-09-08
**Windows installer built, automated smoke passed, GitHub prerelease published.**

- Release: https://github.com/dushavolka1-design/Misha-debil/releases/tag/docly-windows-0.1.0-ci.5.1
- EXE: https://github.com/dushavolka1-design/Misha-debil/releases/download/docly-windows-0.1.0-ci.5.1/Docly-Setup-x64.exe
- Build output: `release/Docly-Setup-x64.exe`; binary is a release asset, not committed into Git source history.
- Size: **3,053,048 bytes**.
- SHA256: `936ceeb7b6a5bf652f09d7fd80e1e5eaa3ac3142240557ccae112723f845c549` (matches GitHub asset digest).
- Released source: `47873cda75018ebc3c58bb78f138ce60e06308e4`.
- Successful run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258968767
- Full checks: `installer/CI-RESULT.md` and release asset `smoke-results.txt`.
- PR: https://github.com/dushavolka1-design/Misha-debil/pull/2 (base master). No merge performed.

## Scope and baseline
Working branch `chore/docly-fast-windows-installer` was created from master `7ab48303efa92b2e52702256dcdd360c9540d273`. astra/docly-windows-installer-20260906 had the same baseline SHA. fix/docly-desktop-upgrade-safety was inspected at `59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d`; no unrelated changes imported.

IMPORTANT: master desktop launcher uses SQLite/file storage, not PostgreSQL/Redis/Alembic. This existing architecture is preserved. No changes to product API, UI, document analysis, database schema or existing launcher files. Only existing `package.json` was modified; other additions are installer/CI/support files.

## Implemented files
- `installer/docly.iss`
- `installer/build-installer.ps1`
- `installer/prerequisites.ps1`
- `installer/first-run.ps1`
- `installer/check-running.ps1`
- `installer/smoke-test.ps1`
- `installer/README.md`
- `installer/.gitignore`, `release/.gitignore`
- `.github/workflows/windows-installer.yml`
- `.github/workflows/installer-diagnostics.yml`
- `installer/STATUS.md`, `installer/CI-RESULT.md`, `installer/DIAGNOSTICS.md` (last file contains historical failure diagnostics, NOT the final release result).
- `package.json`: added `installer:windows` command.

## Verified on Windows Server 2022 CI
- Clean install to LOCALAPPDATA/Programs/Docly, both shortcuts, installed-programs registration.
- Shipped payload excludes .git, real .env, prebuilt venv and node_modules.
- First-run Python venv, original Python requirements, local pnpm 9.15.9, frozen JS dependencies, production Next.js build including typechecking, existing font/icon verification.
- Generated random session secret; ALLOW_FAKE_PROVIDERS=true.
- Existing SQLite initialization/migration, default ports 8000/3000.
- HTTP 200 for `/live`, `/ready`, `/app/analyzer`.
- Second launch reuses API/Web processes and preserves secret.
- Launcher stop terminates API/Web.
- Reinstall preserves .env and user database.
- Standard registered uninstaller removes registration, shortcuts, launcher and generated venv; preserves user data/configuration.
- Inno Setup compilation and Windows PowerShell syntax passed; local JSON/YAML parsing and payload-filter regressions passed.

## Installer-only blockers fixed during CI
Windows PowerShell native argument quoting; exclusion of installer/uninstaller from runtime-process detection; preservation of upload UI source; inclusion of required non-secret `sources/allowlist.json`. No unrelated product fixes.

## Rebuild
On Windows x64 with Git, Inno Setup 6.3+ and pnpm: `pnpm installer:windows`.
Alternatively: `powershell -NoProfile -ExecutionPolicy Bypass -File installer/build-installer.ps1`.
Node.js 20+ x64 and Python 3.12+ x64 are checked at installation. Missing dependencies offer winget or official download pages. First run downloads pnpm/JS/Python dependencies; Noto Sans is verified and downloaded only if missing/mismatched. No Docker, PostgreSQL or Redis runtime installation in this preserved desktop profile.

## Remaining limitations / next work
- This is an **unsigned prerelease**, not a fully certified Windows 10/11 release. Manual Windows 10/11 GUI, browser-opening and missing-dependency/winget scenarios remain untested. Headless CI validates the analyzer HTTP route, not a human browser session.
- Requires internet on first run; Node/Python are not embedded. Original Python version ranges remain; no mass dependency changes.
- Existing unrelated monorepo JS/Python/security checks fail. They were not fixed; PR not merged into master.
- Data, .env and logs intentionally survive uninstall. Existing Docly processes must be stopped first; no unsafe blanket process killing.
- Do not confuse historical DIAGNOSTICS.md failures with the successful final CI-RESULT.md.
- Use `[skip ci]` for checkpoint-only commits. Do not change the product architecture to add PostgreSQL/Redis just to match the outdated prompt.
