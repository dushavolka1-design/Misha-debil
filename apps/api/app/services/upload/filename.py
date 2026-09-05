from __future__ import annotations

import re
import unicodedata

# Bidirectional / override controls used in spoofing
_BIDI = dict.fromkeys(
    (
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
        "\u2066",
        "\u2067",
        "\u2068",
        "\u2069",
        "\u200e",
        "\u200f",
    ),
    None,
)

_CTRL = re.compile(r"[\x00-\x1f\x7f]")
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._\- ()\[\]]+")


def sanitize_display_filename(name: str | None, *, max_len: int = 180) -> str:
    """Human-facing label only — never use as storage key/path/header."""
    raw = (name or "document").strip() or "document"
    raw = unicodedata.normalize("NFKC", raw)
    raw = raw.translate(_BIDI)
    raw = _CTRL.sub("", raw)
    raw = raw.replace("\\", "_").replace("/", "_")
    raw = _SAFE_CHARS.sub("_", raw)
    raw = raw.strip(" .") or "document"
    if len(raw) > max_len:
        stem, _, ext = raw.rpartition(".")
        if ext and len(ext) <= 8:
            keep = max_len - len(ext) - 1
            raw = f"{stem[:keep]}.{ext}"
        else:
            raw = raw[:max_len]
    return raw


def opaque_object_key(*, tenant_id: str, document_id: str, kind: str, ext: str) -> str:
    """Storage path never includes original filename."""
    safe_ext = re.sub(r"[^a-z0-9]", "", ext.lower())[:8] or "bin"
    return f"t/{tenant_id}/d/{document_id}/{kind}.{safe_ext}"
