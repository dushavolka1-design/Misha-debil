# Docly Windows installer — checkpoint

## 2026-09-08: verified baseline
- Working branch: `chore/docly-fast-windows-installer`, created from `master` at `7ab48303efa92b2e52702256dcdd360c9540d273`.
- `astra/docly-windows-installer-20260906` has the same SHA.
- `fix/docly-desktop-upgrade-safety` points at `59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d`; no unrelated changes imported.
- IMPORTANT: current master uses the desktop SQLite/file-storage profile, NOT PostgreSQL/Redis. `docly_launcher.py`, `setup-desktop.ps1` and `desktop_boot.py` explicitly implement this. Preserve the existing architecture. PostgreSQL/Redis/Alembic smoke checks do not apply to this launcher.
- Existing silent VBS requires a pre-created venv; installer needs a first-run bootstrap before delegating to it.
- Assistant sandbox is Linux, has no Wine/Inno/PowerShell, and cannot resolve github.com. GitHub MCP read/write works. Windows build and smoke must run on GitHub Actions or a real Windows machine.

## Current status
Branch created; installer implementation in progress. No EXE built yet. No installation/launch/uninstall tests have passed yet. Do not describe this as a completed release.

## Next steps
1. Add Inno Setup config, explicit filtered payload staging, prerequisite detection with Russian messages/winget, and first-run wrapper.
2. Add Windows Actions build + installation/launch/uninstall smoke; publish only if smoke passes.
3. Inspect actual CI result and record EXE size, SHA256, test evidence and release link here.
4. If Actions cannot be written or run with this connection, preserve files and report the exact blocker instead of claiming a release.
