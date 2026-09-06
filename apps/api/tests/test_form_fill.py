from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.forms.fill.coord_map import CoordinateMap, format_value
from app.services.forms.fill.engine import FillError, extract_static_text, fill_pdf, page_geometry
from app.services.forms.fill.pixel_diff import TECHNICAL_TOLERANCE, compare_underlay_vs_output
from app.services.forms.fill.service import FormFillService
from app.services.forms.fill.underlay import build_demo_a4_underlay
from app.services.forms.fill.validate import validate_inputs

ARTIFACT_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "pixel-diff"


@pytest.fixture()
def fill_service() -> FormFillService:
    svc = FormFillService()
    svc.seed_demo_published()
    return svc


def test_underlay_hash_verified_before_generate(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    with pytest.raises(FillError) as ei:
        fill_pdf(
            underlay_pdf=ver.original_pdf,
            underlay_hash="0" * 64,
            coord_map=ver.coord_map,
            answers={"full_name": "Ivan", "doc_date": "2026-01-15"},
        )
    assert ei.value.code == "underlay_hash_mismatch"


def test_signature_stamp_left_empty(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    preview = validate_inputs(
        ver.coord_map,
        {"full_name": "Ivan", "doc_date": "2026-01-15", "signature": "SIGN", "stamp": "SEAL"},
    )
    assert not preview.ok
    assert any(i.code == "reserved_no_fill" for i in preview.issues)
    assert "signature" in preview.skipped_reserved


def test_overflow_reject_no_shrink(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    long_name = "A" * 200
    preview = validate_inputs(ver.coord_map, {"full_name": long_name, "doc_date": "2026-01-15"})
    assert any(i.code == "overflow_length" for i in preview.issues)


def test_preview_forbidden_chars_and_required(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    preview = validate_inputs(ver.coord_map, {"full_name": "Name@", "doc_date": ""})
    codes = {i.code for i in preview.issues}
    assert "forbidden_chars" in codes
    assert "required_empty" in codes


def test_date_formatter_and_cyrillic_latin(fill_service: FormFillService) -> None:
    assert format_value("2026-03-01", "date_ru") == "01.03.2026"
    ver = next(iter(fill_service.versions.values()))
    preview = validate_inputs(
        ver.coord_map,
        {"full_name": "Иван Ivan", "doc_date": "2026-03-01", "notes": "ok"},
    )
    assert preview.ok
    assert preview.normalized["doc_date"] == "01.03.2026"


def test_wrap_and_empty_optional(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    notes = "word " * 30
    preview = validate_inputs(
        ver.coord_map,
        {"full_name": "Short", "doc_date": "2026-01-15", "notes": notes},
    )
    # wrap strategy → warning ok
    assert preview.ok or any(i.code in {"wrap_applied", "clip_applied"} for i in preview.issues)
    empty_notes = validate_inputs(ver.coord_map, {"full_name": "Short", "doc_date": "2026-01-15"})
    assert empty_notes.ok


def test_four_eyes_review(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    # Create draft awaiting review from new map
    draft = fill_service.submit_coord_map_for_review(
        form_version_id=ver.id,
        map_json=ver.coord_map.to_json(),
        author_id="alice",
    )
    with pytest.raises(FillError) as ei:
        fill_service.approve_coord_map(draft.id, reviewer_id="alice")
    assert ei.value.code == "four_eyes"
    fill_service.approve_coord_map(draft.id, reviewer_id="bob")
    assert fill_service.versions[ver.id].review_status == "published"
    assert fill_service.versions[ver.id].second_reviewer_id == "bob"


def test_blocked_version_not_generated_keeps_old(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    from uuid import uuid4

    uid = uuid4()
    gen = fill_service.generate(
        form_version_id=ver.id,
        user_id=uid,
        answers={"full_name": "Ivan Petrov", "doc_date": "2026-01-15"},
    )
    assert gen.output_pdf.startswith(b"%PDF")
    fill_service.block_version_for_new(ver.id, "source superseded")
    with pytest.raises(FillError) as ei:
        fill_service.generate(
            form_version_id=ver.id,
            user_id=uid,
            answers={"full_name": "Ivan", "doc_date": "2026-01-15"},
        )
    assert ei.value.code == "version_blocked"
    # Previously created still accessible
    kept = fill_service.get_generated(gen.id, user_id=uid)
    assert kept.output_hash == gen.output_hash
    fill_service.delete_generated(gen.id, user_id=uid)
    with pytest.raises(FillError):
        fill_service.get_generated(gen.id, user_id=uid)


def test_pixel_diff_outside_mask_and_static_text(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    result = fill_pdf(
        underlay_pdf=ver.original_pdf,
        underlay_hash=ver.original_hash,
        coord_map=ver.coord_map,
        answers={"full_name": "Ivan Petrov", "doc_date": "2026-01-15", "notes": "line one"},
    )
    assert result.page_count == 1
    geom_u = page_geometry(ver.original_pdf)
    geom_o = page_geometry(result.output_pdf)
    assert geom_u == geom_o

    under_text = extract_static_text(ver.original_pdf)
    out_text = extract_static_text(result.output_pdf)
    report = compare_underlay_vs_output(
        underlay_pdf=ver.original_pdf,
        output_pdf=result.output_pdf,
        coord_map=ver.coord_map,
        dpi=120,
        underlay_text=under_text,
        output_text=out_text,
    )
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / "form_fill_pixel_diff.json"
    report.write_artifact(artifact)
    assert artifact.is_file()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["tolerance"] == TECHNICAL_TOLERANCE
    assert report.page_count_match
    assert report.passed, payload
    # Outside mask must be within technical tolerance
    assert all(p.outside_max_delta <= TECHNICAL_TOLERANCE for p in report.pages)


def test_golden_max_short_empty_a4(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    cases = [
        {"full_name": "A", "doc_date": "2026-01-01"},
        {"full_name": "B" * 40, "doc_date": "2026-12-31"},
        {"full_name": "Latin Name", "doc_date": "2026-06-15", "notes": ""},
        {"full_name": "Кириллица", "doc_date": "2026-06-15", "notes": "перенос текста пример"},
    ]
    for answers in cases:
        r = fill_pdf(
            underlay_pdf=ver.original_pdf,
            underlay_hash=ver.original_hash,
            coord_map=ver.coord_map,
            answers=answers,
        )
        assert r.page_boxes[0][2] > 500  # A4 width
        assert r.engine_version
        assert r.template_hash == ver.original_hash


def test_arrival_notice_catalog_not_fillable_without_official_source() -> None:
    from app.services.forms.catalog import FormCatalogService
    from app.services.forms.catalog_seed import seed_prompt6_catalog
    from app.services.sources.registry import SourceRegistry

    catalog = FormCatalogService(SourceRegistry())
    seed_prompt6_catalog(catalog)
    catalog_id = catalog.by_slug["mvd.arrival_notice.app4"]
    rec = catalog.get(catalog_id)
    assert rec.fill_ready is False
    card = catalog.card(rec)
    svc = FormFillService()
    pkg = svc.fill_package(catalog_form_id=catalog_id, catalog_card=card)
    assert pkg["available"] is False
    assert "underlay_url" not in pkg
    assert pkg.get("checklist")


def test_medical_memo_fill_preview_pdf_has_banners() -> None:
    from uuid import uuid4

    from app.services.forms.catalog import FormCatalogService
    from app.services.forms.catalog_seed import link_fill_version, seed_prompt6_catalog
    from app.services.sources.registry import SourceRegistry

    catalog = FormCatalogService(SourceRegistry())
    seed_prompt6_catalog(catalog)
    svc = FormFillService(catalog=catalog)
    catalog_id = catalog.by_slug["medical.visit.memo"]
    ver = svc.seed_medical_memo_published(catalog_form_id=catalog_id)
    linked = link_fill_version(catalog, slug="medical.visit.memo", fill_version_id=ver.id)
    assert linked.fill_ready is True
    card = catalog.card(catalog.get(catalog_id))
    pkg = svc.fill_package(catalog_form_id=catalog_id, catalog_card=card)
    assert pkg["available"] is True
    preview = svc.preview(ver.id, {"visit_date": "2026-01-15", "questions": "Какие анализы нужны"})
    assert preview.ok
    gen = svc.generate(
        form_version_id=ver.id,
        user_id=uuid4(),
        answers={"visit_date": "2026-01-15", "questions": "Какие анализы нужны"},
    )
    text = "\n".join(extract_static_text(gen.output_pdf))
    assert "НЕ ЯВЛЯЕТСЯ СПРАВКОЙ" in text or "НЕ СПРАВКА" in text
    lowered = text.lower()
    assert "диагноз" not in lowered or "не содержит" in lowered or "нет печати" in lowered
    assert gen.output_pdf.startswith(b"%PDF")
    assert len(page_geometry(gen.output_pdf)) == 2


def test_generate_rejects_invalid_preview(fill_service: FormFillService) -> None:
    ver = next(iter(fill_service.versions.values()))
    from uuid import uuid4

    with pytest.raises(FillError) as ei:
        fill_service.generate(
            form_version_id=ver.id,
            user_id=uuid4(),
            answers={"full_name": "@" * 5, "doc_date": ""},
        )
    assert ei.value.code == "validation_failed"


def test_unpublished_not_generated() -> None:
    svc = FormFillService()
    under = build_demo_a4_underlay()
    # manually insert draft version
    from datetime import date
    from uuid import uuid4

    from app.services.forms.fill.service import FormVersionRecord

    cmap = CoordinateMap(version="x", page_count=1, fields=[], page_boxes=under.page_boxes)
    ver = FormVersionRecord(
        id=uuid4(),
        slug="draft.only",
        form_version="0.0.1",
        title="draft",
        original_pdf=under.pdf_bytes,
        original_hash=under.content_hash,
        page_geometry=under.page_boxes,
        coord_map=cmap,
        coord_map_hash=cmap.content_hash(),
        allowed_font_name="x",
        allowed_font_hash="y",
        font_license="n/a",
        field_schema={},
        valid_from=date(2024, 1, 1),
        valid_to=None,
        review_status="draft",
        author_id="a",
    )
    svc.versions[ver.id] = ver
    with pytest.raises(FillError) as ei:
        svc.generate(form_version_id=ver.id, user_id=uuid4(), answers={})
    assert ei.value.code == "not_published"
