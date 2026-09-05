from __future__ import annotations

import hashlib
import io
import struct
import zipfile
from dataclasses import dataclass
from enum import StrEnum
from xml.etree import ElementTree as ET


class DetectedType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    JPEG = "jpeg"
    PNG = "png"


MIME_BY_TYPE: dict[DetectedType, str] = {
    DetectedType.PDF: "application/pdf",
    DetectedType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    DetectedType.JPEG: "image/jpeg",
    DetectedType.PNG: "image/png",
}

EXT_BY_TYPE: dict[DetectedType, str] = {
    DetectedType.PDF: "pdf",
    DetectedType.DOCX: "docx",
    DetectedType.JPEG: "jpg",
    DetectedType.PNG: "png",
}

ALLOWED_EXTENSIONS = frozenset({"pdf", "docx", "jpg", "jpeg", "png"})

# Defaults (plan may tighten)
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_DOCX_UNCOMPRESSED = 200 * 1024 * 1024
MAX_DOCX_RATIO = 100
MAX_DOCX_FILES = 2_000


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    detected: DetectedType | None
    content_type: str | None
    sha256: str
    reason: str | None = None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_magic(data: bytes) -> DetectedType | None:
    if data.startswith(b"%PDF"):
        return DetectedType.PDF
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedType.PNG
    if data.startswith(b"\xff\xd8\xff"):
        return DetectedType.JPEG
    if data.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
                if "[Content_Types].xml" in names and any(n.startswith("word/") for n in names):
                    return DetectedType.DOCX
        except zipfile.BadZipFile:
            return None
    return None


def extension_of(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_upload(
    *,
    data: bytes,
    declared_filename: str,
    declared_content_type: str,
    expected_checksum: str | None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> ValidationResult:
    digest = sha256_hex(data)
    if expected_checksum and expected_checksum.lower() != digest:
        return ValidationResult(False, None, None, digest, "checksum_mismatch")
    if len(data) == 0:
        return ValidationResult(False, None, None, digest, "empty_file")
    if len(data) > max_bytes:
        return ValidationResult(False, None, None, digest, "size_exceeded")

    ext = extension_of(declared_filename)
    if ext not in ALLOWED_EXTENSIONS:
        return ValidationResult(False, None, None, digest, "extension_not_allowed")

    detected = _detect_magic(data)
    if detected is None:
        return ValidationResult(False, None, None, digest, "magic_not_recognized")

    # Extension must match magic family
    if detected == DetectedType.PDF and ext != "pdf":
        return ValidationResult(False, detected, None, digest, "extension_magic_mismatch")
    if detected == DetectedType.DOCX and ext != "docx":
        return ValidationResult(False, detected, None, digest, "extension_magic_mismatch")
    if detected == DetectedType.PNG and ext != "png":
        return ValidationResult(False, detected, None, digest, "extension_magic_mismatch")
    if detected == DetectedType.JPEG and ext not in {"jpg", "jpeg"}:
        return ValidationResult(False, detected, None, digest, "extension_magic_mismatch")

    expected_mime = MIME_BY_TYPE[detected]
    declared = (declared_content_type or "").split(";")[0].strip().lower()
    # Accept jpeg aliases
    aliases = {expected_mime}
    if detected == DetectedType.JPEG:
        aliases.add("image/jpg")
    if declared and declared not in aliases:
        return ValidationResult(False, detected, expected_mime, digest, "mime_magic_mismatch")

    return ValidationResult(True, detected, expected_mime, digest, None)


def harden_pdf(data: bytes) -> tuple[bool, str | None]:
    """Reject dangerous PDF features (byte-level heuristics; no JS execution)."""
    if not data.startswith(b"%PDF"):
        return False, "not_pdf"
    # Case-insensitive token scan of raw stream (covers uncompressed dictionaries)
    lowered = data.lower()
    for token, code in (
        (b"/javascript", "pdf_javascript"),
        (b"/js", "pdf_js"),
        (b"/launch", "pdf_launch"),
        (b"/embeddedfile", "pdf_embedded_file"),
        (b"/openaction", "pdf_open_action"),
        (b"/submitform", "pdf_submit_form"),
        (b"/importdata", "pdf_import_data"),
    ):
        if token in lowered:
            return False, code
    # Network / URI actions
    if b"/uri" in lowered and b"http" in lowered:
        return False, "pdf_network_uri"
    return True, None


def harden_docx(data: bytes) -> tuple[bool, str | None]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return False, "docx_bad_zip"

    infos = zf.infolist()
    if len(infos) > MAX_DOCX_FILES:
        return False, "docx_too_many_entries"

    total_uncomp = 0
    for info in infos:
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or name.startswith("../") or "/../" in name or name == "..":
            return False, "docx_path_traversal"
        if info.file_size > MAX_DOCX_UNCOMPRESSED:
            return False, "docx_entry_too_large"
        total_uncomp += info.file_size
        if info.compress_size > 0:
            ratio = info.file_size / max(info.compress_size, 1)
            if ratio > MAX_DOCX_RATIO and info.file_size > 1_000_000:
                return False, "docx_zip_bomb"
        if total_uncomp > MAX_DOCX_UNCOMPRESSED:
            return False, "docx_uncompressed_limit"

        # XXE / external relationships in XML parts
        if name.endswith(".xml") or name.endswith(".rels"):
            try:
                raw = zf.read(info)
            except Exception:
                return False, "docx_read_fail"
            if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
                return False, "docx_xxe"
            if name.endswith(".rels"):
                try:
                    root = ET.fromstring(raw)
                except ET.ParseError:
                    return False, "docx_rels_parse"
                for el in root.iter():
                    mode = el.attrib.get("TargetMode", "")
                    target = el.attrib.get("Target", "")
                    if mode.lower() == "external":
                        return False, "docx_external_relationship"
                    if target.lower().startswith(("http://", "https://", "file:", "ftp:")):
                        return False, "docx_external_target"
    return True, None


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24:
        return None
    # IHDR follows 8-byte signature + 4 length + 4 type
    if data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def _jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or (0xD0 <= marker <= 0xD9):
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2 : i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        i += 2 + length
    return None


def harden_image(data: bytes, detected: DetectedType) -> tuple[bool, str | None]:
    dims = _png_dimensions(data) if detected == DetectedType.PNG else _jpeg_dimensions(data)
    if dims is None:
        return False, "image_dimensions_unreadable"
    w, h = dims
    if w <= 0 or h <= 0:
        return False, "image_invalid_dimensions"
    if w * h > MAX_IMAGE_PIXELS:
        return False, "image_pixels_exceeded"
    # Decode bound: reject absurd individual axis
    if w > 20_000 or h > 20_000:
        return False, "image_axis_exceeded"
    return True, None


def harden_by_type(data: bytes, detected: DetectedType) -> tuple[bool, str | None]:
    if detected == DetectedType.PDF:
        return harden_pdf(data)
    if detected == DetectedType.DOCX:
        return harden_docx(data)
    if detected in {DetectedType.PNG, DetectedType.JPEG}:
        return harden_image(data, detected)
    return False, "unsupported_type"
