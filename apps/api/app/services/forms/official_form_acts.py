"""Official RU legal acts for catalog cards — URLs only from the allowlisted portal.

Do not treat these publications as approved fillable blanks. The portal stores the
legal act (often a multi-page order PDF), not a separately cropped user blank.
Government fill_ready stays false until editorial raw+map approval.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.forms.catalog import FormCatalogService, FormRecord, utcnow

# publication.pravo.gov.ru document ids verified by title on the official portal.
OFFICIAL_FORM_ACTS: dict[str, dict[str, Any]] = {
    "mvd.arrival_notice.app4": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202412240038",
        "organ": "МВД России",
        "act_number": "856",
        "act_date": date(2020, 12, 10),
        "act_title": (
            "Приказ МВД России от 10.12.2020 N 856 (ред. Приказа МВД России от 22.10.2024 N 628), приложение N 4"
        ),
        "appendix": "Приложение N 4",
        "edition_note": "Опубл. 0001202412240038. Бланк не вырезан из акта.",
        "unified_form": True,
        "source_slug": "pravo-arrival-856-628",
        "warning": (
            "Официальный бланк — приложение N 4 к приказу МВД N 856 (ред. N 628). "
            "Источник: publication.pravo.gov.ru, публикация 0001202412240038."
        ),
    },
    "mvd.patent.application": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202210200028",
        "organ": "МВД России",
        "act_number": "635",
        "act_date": date(2017, 8, 14),
        "act_title": (
            "Приказ МВД России от 14.08.2017 N 635, приложение N 1 "
            "в редакции приказа МВД России от 13.09.2022 N 679 "
            "(действует с 31.10.2022)"
        ),
        "appendix": "Приложение N 1 к приказу N 635 (ред. N 679)",
        "edition_note": "Опубл. 0001202210200028. Редакция приложения N 1 — приказ N 679, с 31.10.2022.",
        "unified_form": True,
        "source_slug": "pravo-patent-635-679",
        "warning": (
            "Заявление об оформлении патента — приложение N 1 к приказу МВД N 635 "
            "в редакции приказа N 679 от 13.09.2022 (действует с 31.10.2022). "
            "Официальный источник — publication.pravo.gov.ru. Патент не является разрешением на работу. "
            "Перенесите сведения на бланк территориального органа МВД (страница бланков субъекта)."
        ),
    },
    "mvd.work_notification": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202508220021",
        "organ": "МВД России",
        "act_number": "536",
        "act_date": date(2020, 7, 30),
        "act_title": (
            "Приказ МВД России от 30.07.2020 N 536, приложение N 7, форма 1 "
            "(ред. приказов от 22.11.2023 N 887 и от 06.08.2025 N 552)"
        ),
        "appendix": "Приложение N 7, форма 1",
        "edition_note": (
            "Опубл. 0001202508220021 (изменения в прил. N 7 и N 9). "
            "Исходный приказ — 0001202010190050. Бланк из акта не вырезан автоматически."
        ),
        "unified_form": True,
        "source_slug": "pravo-work-notify-536-552",
        "warning": (
            "Форма 1 уведомления о заключении трудового или гражданско-правового договора — "
            "приложение N 7 к приказу МВД N 536 в редакции приказа N 552 от 06.08.2025. "
            "Официальный текст: publication.pravo.gov.ru, 0001202508220021. "
            "Бланк территориального органа совпадает с формой 1; перенесите сведения на тот бланк "
            "(страница бланков субъекта МВД). Расторжение договора — приложение N 9 к тому же приказу."
        ),
    },
    "mvd.rvp.application": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202007070036",
        "organ": "МВД России",
        "act_number": "407",
        "act_date": date(2020, 6, 8),
        "act_title": (
            "Приказ МВД России от 08.06.2020 N 407 — административный регламент "
            "по выдаче разрешения на временное проживание и формы"
        ),
        "appendix": "Формы к приказу N 407",
        "edition_note": "Опубл. 0001202007070036. Бланк не вырезан из акта.",
        "unified_form": True,
        "source_slug": "pravo-rvp-407",
        "warning": (
            "Заявление о выдаче РВП относится к регламенту МВД N 407. "
            "Источник: publication.pravo.gov.ru, публикация 0001202007070036."
        ),
    },
    "mvd.vnz.application": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202007070035",
        "organ": "МВД России",
        "act_number": "417",
        "act_date": date(2020, 6, 11),
        "act_title": (
            "Приказ МВД России от 11.06.2020 N 417 — административный регламент по выдаче вида на жительство"
        ),
        "appendix": "Формы к приказу N 417",
        "edition_note": "Опубл. 0001202007070035. Бланк не вырезан из акта.",
        "unified_form": True,
        "source_slug": "pravo-vnz-417",
        "warning": (
            "Заявление о выдаче ВНЖ относится к регламенту МВД N 417. "
            "Источник: publication.pravo.gov.ru, публикация 0001202007070035."
        ),
    },
    "mvd.invitation.business": {
        "official_url": "https://publication.pravo.gov.ru/document/0001202012020009",
        "organ": "МВД России",
        "act_number": "677",
        "act_date": date(2020, 9, 29),
        "act_title": (
            "Приказ МВД России от 29.09.2020 N 677 — административный регламент "
            "по оформлению и выдаче приглашений на въезд в РФ"
        ),
        "appendix": "Формы к приказу N 677",
        "edition_note": "Опубл. 0001202012020009. Бланк не вырезан из акта.",
        "unified_form": True,
        "source_slug": "pravo-invitation-677",
        "warning": (
            "Ходатайство о приглашении относится к регламенту МВД N 677. "
            "Источник: publication.pravo.gov.ru, публикация 0001202012020009."
        ),
    },
    "mvd.stay_extension": {
        "official_url": "https://publication.pravo.gov.ru/",
        "organ": "МВД России",
        "act_number": "115-ФЗ",
        "act_date": date(2002, 7, 25),
        "act_title": (
            "Федеральный закон от 25.07.2002 N 115-ФЗ — срок временного пребывания; "
            "единая форма заявления на все основания на портале не опубликована"
        ),
        "appendix": None,
        "edition_note": "Единый бланк не найден на publication.pravo.gov.ru.",
        "unified_form": False,
        "source_slug": "pravo-stay-extension-115fz",
        "warning": (
            "Единого бланка продления срока пребывания для всех оснований на publication.pravo.gov.ru нет. "
            "Состав сведений зависит от основания в 115-ФЗ и территориального органа."
        ),
    },
}


def act_for_slug(slug: str) -> dict[str, Any] | None:
    return OFFICIAL_FORM_ACTS.get(slug)


def apply_official_act_metadata(catalog: FormCatalogService) -> None:
    """Stamp allowlisted act metadata onto government cards. Never publishes fill_ready."""
    for rec in list(catalog.iter_records()):
        if not isinstance(rec, FormRecord) or rec.form_kind != "government_form":
            continue
        spec = OFFICIAL_FORM_ACTS.get(rec.slug)
        if not spec:
            continue
        catalog.update_fields(
            rec.id,
            act_number=spec["act_number"],
            act_date=spec["act_date"],
            act_title=spec["act_title"],
            authority=spec["organ"],
            organ=spec["organ"],
            warning=spec["warning"],
            edition_note=spec["edition_note"],
            fill_ready=False,
            status="needs_review" if rec.status == "published" and rec.source_snapshot_id is None else rec.status,
        )


def try_fetch_official_acts(registry: Any, catalog: FormCatalogService) -> list[dict[str, Any]]:
    """Best-effort fetch of official HTML/PDF. Failures stay visible; never auto-approve."""
    log: list[dict[str, Any]] = []
    if not getattr(registry, "fetch_fn", None):
        return [{"result": "skipped", "reason": "fetcher_unavailable"}]
    for slug, spec in OFFICIAL_FORM_ACTS.items():
        url = spec["official_url"]
        if url.rstrip("/").endswith("pravo.gov.ru"):
            log.append({"slug": slug, "result": "skipped_generic_portal", "url": url})
            continue
        source_slug = spec["source_slug"]
        try:
            src_id = registry.by_slug.get(source_slug)
            if src_id:
                src = registry.sources[src_id]
            else:
                src = registry.discover(
                    slug=source_slug,
                    title=spec["act_title"],
                    official_url=url,
                    organ=spec["organ"],
                    actor="official_bootstrap",
                )
            snap = registry.fetch_and_parse(src.id, actor="official_bootstrap", conditional=True)
            form_id = catalog.by_slug.get(slug)
            if form_id and snap.raw:
                rec = catalog.get(form_id)
                # Snapshot of the legal act, not a cropped official blank — do not store as form raw.
                catalog.update_fields(
                    rec.id,
                    source_snapshot_id=snap.id,
                    fill_ready=False,
                )
            log.append(
                {
                    "slug": slug,
                    "result": "fetched" if snap.raw else "empty",
                    "snapshot_id": str(snap.id),
                    "state": snap.state.value if hasattr(snap.state, "value") else str(snap.state),
                    "bytes": len(snap.raw or b""),
                    "at": utcnow().isoformat(),
                },
            )
        except Exception as exc:  # noqa: BLE001 — bootstrap must not crash desktop start
            log.append({"slug": slug, "result": "fetch_failed", "error": type(exc).__name__, "url": url})
    catalog.verification_log.extend(log)
    return log
