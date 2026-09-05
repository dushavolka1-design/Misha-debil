"""Prompt 3: no government forms on synthetic underlays; font pin; honest catalog."""

from __future__ import annotations

import hashlib
import inspect
from datetime import date
from uuid import uuid4

import pytest

from app.services.forms.catalog import FormCatalogService
from app.services.forms.catalog_seed import PROMPT6_CARDS, link_fill_version, seed_prompt6_catalog
from app.services.forms.fill.engine import FillError, extract_static_text, fill_pdf, page_geometry
from app.services.forms.fill.fonts import ASSETS, MANIFEST, assert_bundled_font, bundled_font_status, resolve_allowed_font
from app.services.forms.fill.service import FormFillService, FormVersionRecord
from app.services.forms.fill.underlay import SYNTHETIC_MARKER, build_demo_a4_underlay
from app.services.sources.registry import SourceRegistry


def test_bundled_font_exists_with_pinned_sha256() -> None:
    status = bundled_font_status()
    assert status.ok, status.reason
    assert_bundled_font()
    path = resolve_allowed_font()
    assert path.name == "NotoSans-Regular.ttf"
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = __import__("json").loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest.get("expected_sha256"), "expected_sha256 must be pinned"
    assert actual == manifest["expected_sha256"]
    assert (ASSETS / "LICENSE").is_file()
    license_text = (ASSETS / "LICENSE").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in license_text.upper()
    assert "Arial" not in license_text


def test_font_resolver_has_no_system_fallback() -> None:
    import app.services.forms.fill.fonts as fonts_mod

    source = inspect.getsource(fonts_mod)
    assert "arial.ttf" not in source.lower()
    assert "segoeui" not in source.lower()
    assert "/usr/share/fonts" not in source
    assert "C:/Windows/Fonts" not in source


def test_synthetic_underlay_is_not_named_official() -> None:
    under = build_demo_a4_underlay()
    joined = "\n".join(extract_static_text(under.pdf_bytes))
    assert "OFFICIAL FORM UNDERLAY" not in joined
    assert "официальн" not in joined.lower()
    assert SYNTHETIC_MARKER.decode("ascii") in joined or SYNTHETIC_MARKER in under.pdf_bytes


def test_seed_demo_uses_test_synthetic_slug() -> None:
    svc = FormFillService()
    ver = svc.seed_demo_published()
    assert ver.slug.startswith("test.synthetic.")
    assert ver.source_snapshot_id is None
    assert not hasattr(svc, "seed_arrival_notice_published")


def test_government_cannot_generate_on_synthetic_underlay() -> None:
    svc = FormFillService()
    under = build_demo_a4_underlay()
    cmap = svc._demo_coord_map(under)
    font_path = resolve_allowed_font()
    from app.services.forms.fill.fonts import font_hash

    ver = FormVersionRecord(
        id=uuid4(),
        slug="mvd.arrival_notice.app4",
        form_version="1.0.0",
        title="Уведомление о прибытии",
        original_pdf=under.pdf_bytes,
        original_hash=under.content_hash,
        page_geometry=under.page_boxes,
        coord_map=cmap,
        coord_map_hash=cmap.content_hash(),
        allowed_font_name=font_path.name,
        allowed_font_hash=font_hash(font_path),
        font_license="OFL-1.1",
        field_schema={"full_name": {"required": True}, "doc_date": {"required": True}},
        valid_from=date(2024, 1, 1),
        valid_to=None,
        review_status="published",
        author_id="a",
        second_reviewer_id="b",
        published_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    svc.versions[ver.id] = ver
    with pytest.raises(FillError) as ei:
        svc.generate(
            form_version_id=ver.id,
            user_id=uuid4(),
            answers={"full_name": "Ivan Petrov", "doc_date": "2026-01-15"},
        )
    assert ei.value.code in {"synthetic_underlay_forbidden", "source_snapshot_missing"}


def test_arrival_card_is_not_fill_ready_without_official_source() -> None:
    catalog = FormCatalogService(SourceRegistry())
    seed_prompt6_catalog(catalog)
    rec = catalog.get(catalog.by_slug["mvd.arrival_notice.app4"])
    assert rec.fill_ready is False
    assert rec.status != "published" or rec.source_snapshot_id is None
    card = catalog.card(rec)
    assert card["fill_ready"] is False
    assert card["unavailable_reason"]
    pkg = FormFillService().fill_package(catalog_form_id=rec.id, catalog_card=card)
    assert pkg["available"] is False
    assert "underlay_url" not in pkg
    assert pkg.get("checklist")
    forbidden = " ".join(
        [
            pkg.get("unavailable_reason") or "",
            pkg.get("checklist_hint") or "",
            str(pkg.get("checklist")),
        ],
    ).lower()
    for token in ("raw", "fixture", "fill version", "needs_review", "approved"):
        assert token not in forbidden


def test_catalog_cannot_mark_government_fill_ready_while_unpublished() -> None:
    catalog = FormCatalogService(SourceRegistry())
    seed_prompt6_catalog(catalog)
    rec = catalog.get(catalog.by_slug["mvd.patent.application"])
    catalog.update_fields(rec.id, fill_ready=True, fill_version_id=uuid4())
    rec2 = catalog.get(rec.id)
    assert rec2.fill_ready is False
    arrival = next(s for s in PROMPT6_CARDS if s["slug"] == "mvd.arrival_notice.app4")
    assert arrival["fill_ready"] is False


def test_link_fill_version_does_not_publish_government_without_source() -> None:
    catalog = FormCatalogService(SourceRegistry())
    seed_prompt6_catalog(catalog)
    rec = link_fill_version(catalog, slug="mvd.arrival_notice.app4", fill_version_id=uuid4())
    assert rec.fill_ready is False


def test_pixel_engine_embeds_font_and_keeps_a4() -> None:
    svc = FormFillService()
    ver = svc.seed_demo_published()
    result = fill_pdf(
        underlay_pdf=ver.original_pdf,
        underlay_hash=ver.original_hash,
        coord_map=ver.coord_map,
        answers={"full_name": "Иван Петров-Ivan", "doc_date": "2026-01-15", "notes": "адрес " * 8},
    )
    assert result.output_pdf.startswith(b"%PDF")
    assert b"/FontFile2" in result.output_pdf or b"FormFillAllowed" in result.output_pdf
    boxes = page_geometry(result.output_pdf)
    assert boxes[0][2] > 500
    assert boxes[0][3] > 800
    static = "\n".join(extract_static_text(ver.original_pdf))
    out = "\n".join(extract_static_text(result.output_pdf))
    for label in ("Static label: Full name", "Static label: Date"):
        assert label in static
        assert label in out


def test_long_name_and_address_overflow_or_wrap() -> None:
    svc = FormFillService()
    ver = svc.seed_demo_published()
    from app.services.forms.fill.validate import validate_inputs

    long_fio = "Александр " * 20
    preview = validate_inputs(ver.coord_map, {"full_name": long_fio, "doc_date": "2026-01-15"})
    assert not preview.ok or any(i.code in {"overflow_length", "wrap_applied", "clip_applied"} for i in preview.issues)
    addr = validate_inputs(
        ver.coord_map,
        {
            "full_name": "Short",
            "doc_date": "2026-01-15",
            "notes": "ул. Длинная, д. 1, корп. 2, кв. 345, " * 6,
        },
    )
    assert addr.ok or any(i.code in {"wrap_applied", "clip_applied", "overflow_length"} for i in addr.issues)
