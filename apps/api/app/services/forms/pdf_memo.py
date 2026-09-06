from __future__ import annotations

"""Medical memo PDF — never an official medical org document."""

from typing import Any

MEDICAL_PDF_BANNER = "Предварительная анкета/памятка. Не является медицинским документом."

# Explicit denylist — backend must reject even if UI is bypassed
FORBIDDEN_MEDICAL_ARTIFACTS = frozenset(
    {
        "certificate",
        "official_certificate",
        "certificat",
        "conclusion",
        "medical_conclusion",
        "zaklyuchenie",
        "spravka",
        "medical_certificate",
        "medical_spravka",
        "analysis_result",
        "lab_result",
        "diagnosis",
        "diagnoz",
        "signed_document",
        "with_signature",
        "signature",
        "with_stamp",
        "stamp",
        "seal",
        "pechat",
        "with_qr",
        "qr",
        "qr_code",
        "institution_number",
        "org_number",
        "letterhead",
        "blank_uchrezhdeniya",
    },
)

ALLOWED_MEDICAL_ARTIFACTS = frozenset({"questionnaire", "checklist", "memo", "pamphlet"})


class MedicalPdfError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def assert_medical_artifact_allowed(kind: str) -> str:
    k = (kind or "").strip().lower()
    if k in FORBIDDEN_MEDICAL_ARTIFACTS or any(
        x in k for x in ("certificate", "spravka", "diagnosis", "stamp", "qr", "seal")
    ):
        raise MedicalPdfError(
            "forbidden_medical_artifact",
            f"Forbidden medical artifact kind: {kind}",
            http_status=403,
        )
    if k not in ALLOWED_MEDICAL_ARTIFACTS:
        raise MedicalPdfError(
            "forbidden_medical_artifact",
            f"Artifact kind not allowed: {kind}",
            http_status=403,
        )
    return k


def render_medical_memo_pdf(
    *,
    kind: str,
    title: str,
    body_lines: list[str],
    answers: dict[str, str] | None = None,
) -> bytes:
    kind = assert_medical_artifact_allowed(kind)
    answers = answers or {}

    lines = [
        "Document Analyzer RF — Medical helper PDF",
        f"Kind: {kind}",
        "",
        "BANNER:",
        MEDICAL_PDF_BANNER,
        "This file is NOT an official medical certificate, conclusion, spravka,",
        "diagnosis, analysis result, signed/stamped document, QR, or institution form.",
        "",
        f"Title: {title}",
        "",
    ]
    for line in body_lines:
        lines.append(str(line)[:200])
    if answers:
        lines.append("")
        lines.append("Answers (user-provided, unverified):")
        for k, v in answers.items():
            lines.append(f"- {k}: {str(v)[:120]}")
    lines.append("")
    lines.append(MEDICAL_PDF_BANNER)

    content_lines = ["BT /F1 10 Tf"]
    y = 800
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ascii_line = safe.encode("ascii", "replace").decode("ascii")
        content_lines.append(f"1 0 0 1 40 {y} Tm ({ascii_line}) Tj")
        y -= 14
        if y < 40:
            break
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n",
    )
    objects.append(
        b"4 0 obj<< /Length " + str(len(stream)).encode() + b" >>stream\n" + stream + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(),
    )
    return bytes(out)


def describe_policy() -> dict[str, Any]:
    return {
        "banner": MEDICAL_PDF_BANNER,
        "allowed": sorted(ALLOWED_MEDICAL_ARTIFACTS),
        "forbidden_examples": sorted(FORBIDDEN_MEDICAL_ARTIFACTS),
    }
