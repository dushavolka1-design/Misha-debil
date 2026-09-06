"""Record official-source intake for arrival notice — never invent a PDF."""

from __future__ import annotations

from typing import Any

from app.services.forms.fill.generation_gates import is_test_synthetic_slug, pdf_is_synthetic_underlay
from app.services.forms.catalog import utcnow

# Candidate act known from the official RU legal corpus name only.
# The blank itself must be fetched from an allowlisted official host and approved by humans.
ARRIVAL_OFFICIAL_CANDIDATE = {
    "slug": "mvd.arrival_notice.app4",
    "organ": "МВД России",
    "act_number": "856",
    "act_title": "Приказ МВД России от 10.12.2020 N 856",
    "appendix": "Приложение N 4",
    "source_hosts": ("publication.pravo.gov.ru", "pravo.gov.ru", "mvd.gov.ru"),
    "lookup_urls": (
        "https://publication.pravo.gov.ru/",
        "https://pravo.gov.ru/",
        "https://mvd.gov.ru/",
    ),
}


def record_arrival_editorial_intake(catalog: Any) -> dict[str, Any]:
    """Store editorial work item. Does not download a random PDF or publish a blank."""
    note = {
        "at": utcnow().isoformat(),
        "candidate": ARRIVAL_OFFICIAL_CANDIDATE["slug"],
        "organ": ARRIVAL_OFFICIAL_CANDIDATE["organ"],
        "act_number": ARRIVAL_OFFICIAL_CANDIDATE["act_number"],
        "act_title": ARRIVAL_OFFICIAL_CANDIDATE["act_title"],
        "appendix": ARRIVAL_OFFICIAL_CANDIDATE["appendix"],
        "source_hosts": list(ARRIVAL_OFFICIAL_CANDIDATE["source_hosts"]),
        "lookup_urls": list(ARRIVAL_OFFICIAL_CANDIDATE["lookup_urls"]),
        "result": "awaiting_human_confirmation",
        "reason": (
            "Действующую редакцию бланка нужно взять только с официального российского источника "
            "(портал правовой информации или сайт МВД), сохранить файл без изменений, "
            "записать URL, орган, акт, приложение, даты и контрольную сумму, "
            "затем получить визуальное подтверждение двух редакторов. "
            "Автоматическая публикация и синтетический бланк запрещены."
        ),
    }
    catalog.verification_log.append(note)
    fid = catalog.by_slug.get(ARRIVAL_OFFICIAL_CANDIDATE["slug"])
    if fid:
        rec = catalog.forms.get(fid)
        if rec is not None and rec.form_kind == "government_form":
            catalog.update_fields(
                rec.id,
                act_number=rec.act_number or ARRIVAL_OFFICIAL_CANDIDATE["act_number"],
                act_title=rec.act_title
                or f"{ARRIVAL_OFFICIAL_CANDIDATE['act_title']} ({ARRIVAL_OFFICIAL_CANDIDATE['appendix']})",
                warning=(
                    "Официальный бланк ещё не подтверждён по источнику. Доступен чеклист шагов, бланк не подставляется."
                ),
            )
    return note


def disarm_unofficial_generation(catalog: Any, fill: Any) -> None:
    """Unlink synthetic/unofficial government fill versions from the user catalog."""
    for ver in list(fill.versions.values()):
        synthetic = is_test_synthetic_slug(ver.slug) or pdf_is_synthetic_underlay(ver.original_pdf or b"")
        government = (
            not is_test_synthetic_slug(ver.slug)
            and not ver.slug.startswith("medical.")
            and not ver.slug.startswith("worksheet.")
        )
        if government and (synthetic or ver.source_snapshot_id is None):
            ver.review_status = "blocked_for_new"
            ver.blocked_reason = "Нет подтверждённого официального источника"
            if ver.catalog_form_id:
                fill.by_catalog.pop(ver.catalog_form_id, None)
                ver.catalog_form_id = None
            fill._persist_version(ver)
        if is_test_synthetic_slug(ver.slug) and ver.catalog_form_id:
            fill.by_catalog.pop(ver.catalog_form_id, None)
            ver.catalog_form_id = None
            fill._persist_version(ver)
    for rec in catalog.iter_records():
        if rec.form_kind == "government_form":
            rec.fill_ready = False
            rec.fill_version_id = None
            if rec.status == "published" and rec.source_snapshot_id is None:
                rec.status = "needs_review"
            catalog.update_fields(
                rec.id,
                fill_ready=False,
                fill_version_id=None,
                status=rec.status,
            )
