"""Benign security fixtures — no real malware.

EICAR is the industry-standard harmless AV test string (not executable malware).
"""

from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def minimal_pdf() -> bytes:
    return b"""%PDF-1.4
1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj
2 0 obj<< /Type /Pages /Kids [] /Count 0 >>endobj
trailer<< /Root 1 0 R >>
%%EOF
"""


def pdf_with_javascript() -> bytes:
    return b"""%PDF-1.4
1 0 obj<< /Type /Catalog /OpenAction << /S /JavaScript /JS (app.alert\\(1\\);) >> >>endobj
trailer<< /Root 1 0 R >>
%%EOF
"""


def minimal_png(width: int = 2, height: int = 2) -> bytes:
    # signature + IHDR (no full valid IDAT needed for our dimension checks)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_len = struct.pack(">I", 13)
    ihdr_type = b"IHDR"
    import zlib

    crc = struct.pack(">I", zlib.crc32(ihdr_type + ihdr_data) & 0xFFFFFFFF)
    return sig + ihdr_len + ihdr_type + ihdr_data + crc + struct.pack(">I", 0) + b"IEND" + struct.pack(">I", 0)


def huge_png_declared() -> bytes:
    return minimal_png(width=30_000, height=30_000)


def minimal_jpeg() -> bytes:
    # SOI + SOF0 with 8x8 + EOI
    sof = bytes(
        [
            0xFF,
            0xC0,
            0x00,
            0x0B,
            0x08,
            0x00,
            0x08,
            0x00,
            0x08,
            0x01,
            0x01,
            0x11,
            0x00,
        ],
    )
    return b"\xff\xd8" + sof + b"\xff\xd9"


def minimal_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"></w:document>')
        zf.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>',
        )
    return buf.getvalue()


def docx_with_external_rel() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", '<?xml version="1.0"?><w:document></w:document>')
        zf.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://x" Target="https://evil.example/x" TargetMode="External"/>'
            "</Relationships>",
        )
    return buf.getvalue()


def docx_path_traversal() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<w/>")
        zf.writestr("../evil.txt", "x")
    return buf.getvalue()


def eicar_like_pdf() -> bytes:
    # Harmless AV test string embedded in PDF-like bytes for FakeMalwareScanner
    return b"%PDF-1.4\nEICAR-STANDARD-ANTIVIRUS-TEST-FILE\n%%EOF\n"


def polyglot_png_as_pdf_name() -> bytes:
    return minimal_png()


def pdf_with_text(lines: list[str]) -> bytes:
    """Minimal searchable PDF for analysis e2e (PyMuPDF when available)."""
    try:
        import fitz  # pymupdf

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        y = 72.0
        for line in lines:
            page.insert_text((72.0, y), line, fontsize=12, fontname="helv")
            y += 18.0
        out = doc.tobytes()
        doc.close()
        return out
    except Exception:
        body = "\n".join(lines)
        escaped = body.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
        return (
            b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>endobj\n"
            b"4 0 obj<< /Length "
            + str(len(stream)).encode()
            + b" >>stream\n"
            + stream
            + b"\nendstream endobj\ntrailer<< /Root 1 0 R >>\nstartxref\n0\n%%EOF\n"
        )


LEASE_LINES = [
    "ДОГОВОР АРЕНДЫ № 12/2026",
    "Арендодатель: ООО Ромашка, ИНН 7707083893",
    "Арендатор: ИП Иванов И.И.",
    "Сумма арендной платы: 100 000,00 RUB",
    "Срок: с 01.09.2026 по 31.08.2027",
]

SALE_LINES = [
    "Договор купли-продажи № 7/2026",
    "Продавец: ПАО Пример",
    "Покупатель: ООО Тест",
    "Цена: 50 000 RUB",
]


def write_fixtures() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "clean.pdf").write_bytes(minimal_pdf())
    (ROOT / "lease_contract.pdf").write_bytes(pdf_with_text(LEASE_LINES))
    (ROOT / "sale_contract.pdf").write_bytes(pdf_with_text(SALE_LINES))
    (ROOT / "js.pdf").write_bytes(pdf_with_javascript())
    (ROOT / "clean.png").write_bytes(minimal_png())
    (ROOT / "huge.png").write_bytes(huge_png_declared())
    (ROOT / "clean.jpg").write_bytes(minimal_jpeg())
    (ROOT / "clean.docx").write_bytes(minimal_docx())
    (ROOT / "external.docx").write_bytes(docx_with_external_rel())
    (ROOT / "traversal.docx").write_bytes(docx_path_traversal())
    (ROOT / "eicar.pdf").write_bytes(eicar_like_pdf())
    (ROOT / "README.md").write_text(
        "Benign fixtures for OWASP upload tests. No real malware. EICAR is a standard harmless test string.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    write_fixtures()
