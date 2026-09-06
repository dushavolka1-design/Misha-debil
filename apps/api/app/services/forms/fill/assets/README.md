# Form fill font (OFL)

Distribution includes `NotoSans-Regular.ttf` and `LICENSE` (SIL Open Font License 1.1).

- SHA-256 is pinned in `font-manifest.json`.
- `scripts/windows/install-form-font.ps1` verifies the hash even if the file already exists.
- The fill engine never falls back to Arial or other system fonts.
