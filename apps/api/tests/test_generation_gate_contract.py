from __future__ import annotations

from app.services.forms.fill.generation_gates import catalog_checklist, download_stem


def test_no_version_cannot_claim_map_or_publication_readiness() -> None:
    card = {
        "status": "published",
        "has_raw": True,
        "content_sha256": "synthetic",
        "fill_ready": True,
        "source": {"usable_as_basis": True, "verified": True},
    }
    checks = {item["id"]: item["done"] for item in catalog_checklist(card)}
    assert checks["map"] is False
    assert checks["publish"] is False
    assert checks["visual"] is False


def test_invitation_worksheet_download_name_is_stable() -> None:
    assert download_stem("worksheet.mvd.invitation.business") == "chernovik-hodataystvo-priglashenie"
