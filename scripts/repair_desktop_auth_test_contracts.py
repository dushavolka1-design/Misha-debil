"""Apply reviewed test-only corrections, refusing unexpected source revisions.

Desktop registration consumes its verification token. Acceptance must assert
activation AND reject replay instead of expecting reuse. No app logic changes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

EXPECTED = {
    "apps/api/tests/test_auth_consent.py": ("529290af41017ce45c03f799fb72ca4427b7d690", 2),
    "apps/api/tests/test_form_catalog_api_contract.py": ("2436254ef1055639fd60dd61f9a7930438a78546", 1),
    "apps/api/tests/test_prompt6_acceptance.py": ("ba75e8d8fa275d8a9510100907802915b45ee912", 1),
    "apps/api/tests/test_worksheets_official_acts.py": ("ae771763cb18d16e8c50cbdb2d2c8eaac98e04eb", 1),
}
OLD = '    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200'
NEW = '    assert_desktop_email_is_verified(client, token)'
IMPORT_ANCHOR = 'from fastapi.testclient import TestClient\n'
IMPORT = 'from docly_auth_test_support import assert_desktop_email_is_verified\n'


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def repair(root: Path) -> list[str]:
    updates: dict[Path, str] = {}
    for relative, (expected, occurrences) in EXPECTED.items():
        path = root / relative
        raw = path.read_bytes()
        if git_blob_sha(raw) != expected:
            raise RuntimeError(f"Source changed; review required: {relative}")
        text = raw.decode("utf-8")
        if text.count(OLD) != occurrences or text.count(IMPORT_ANCHOR) != 1:
            raise RuntimeError(f"Unexpected assertion or import count: {relative}")
        text = text.replace(OLD, NEW).replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT)
        if relative.endswith("test_prompt6_acceptance.py"):
            old_name = '"display_name": "Иван Тестов",'
            if text.count(old_name) != 1:
                raise RuntimeError("Unexpected IDOR registration helper")
            text = text.replace(
                old_name,
                '"display_name": "Владелец Тестов" if email == USER_EMAIL else "Другой Тестов",',
            )
        compile(text, relative, "exec")
        updates[path] = text
    # Validate every source before writing any of them.
    for path, text in updates.items():
        path.write_text(text, encoding="utf-8")
    return list(EXPECTED)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for name in repair(root):
        print(f"Updated reviewed desktop auth contract: {name}")
