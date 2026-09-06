"""Reviewed, revision-locked test fixture repair; never changes app behavior."""
from __future__ import annotations

import hashlib
from pathlib import Path


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    if text.count(old) != count:
        raise RuntimeError("Unexpected fixture content; manual review required")
    return text.replace(old, new)


def read_verified(root: Path, relative: str, expected: str) -> str:
    data = (root / relative).read_bytes()
    actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data, usedforsecurity=False).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Unreviewed source revision: {relative}")
    return data.decode("utf-8")


def repair(root: Path) -> None:
    medical_path = "apps/api/tests/test_forms_medical.py"
    medical = read_verified(root, medical_path, "0134267af3b856a5bf81e25a77129bf949d76ea8")
    # The approved source allowlist contains the IDN МВД host, not mvd.gov.ru.
    # Synthetic fetch bodies remain synthetic; no real legal approval is claimed.
    medical = replace_exact(medical, '"mvd.gov.ru"', '"xn--b1aew.xn--p1ai"', 2)

    upload_path = "apps/api/tests/test_upload_lifecycle.py"
    upload = read_verified(root, upload_path, "6d99a1fcacfccb3caa542c3ee7de8145c42c7836")
    upload = replace_exact(upload, "from pathlib import Path\n", "import time\nfrom pathlib import Path\n")
    upload = replace_exact(
        upload,
        "def client(auth_store: AuthConsentStore, doc_service: DocumentLifecycleService):",
        "def client(auth_store: AuthConsentStore):",
    )
    upload = replace_exact(
        upload,
        "        c.app.state.doc_store = doc_service.store\n        c.app.state.doc_service = doc_service\n",
        "        # Keep lifespan-owned services: the real queue consumer holds their\n"
        "        # references. Replacing only HTTP state sends jobs to another store.\n",
    )
    upload = replace_exact(
        upload,
        '    assert put.json()["state"] == "READY"\n    doc_id = body["document_id"]\n',
        '    doc_id = body["document_id"]\n'
        '    # PUT enqueues work; readiness is an asynchronous API contract.\n'
        '    deadline = time.monotonic() + 30.0\n'
        '    while True:\n'
        '        status = client.get(f"/documents/{doc_id}")\n'
        '        assert status.status_code == 200, status.text\n'
        '        state = status.json()["state"]\n'
        '        if state == "READY":\n'
        '            break\n'
        '        assert state in {"QUARANTINED", "SCANNING", "CLEAN", "PROCESSING"}, status.text\n'
        '        assert time.monotonic() < deadline, "Upload did not become READY within 30 seconds"\n'
        '        time.sleep(0.05)\n'
        '    assert client.get(f"/documents/{doc_id}/download").status_code == 200\n',
    )
    updates = {medical_path: medical, upload_path: upload}
    for name, text in updates.items():
        compile(text, name, "exec")
    for name, text in updates.items():
        (root / name).write_text(text, encoding="utf-8")
        print(f"Updated reviewed fixture: {name}")


if __name__ == "__main__":
    repair(Path(__file__).resolve().parents[1])
