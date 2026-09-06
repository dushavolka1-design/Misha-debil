"""Official act metadata and service worksheets — not government blanks."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db import get_engine, get_session_factory
from app.desktop_boot import apply_desktop_env, migrate_sqlite
from app.persistence.sync_db import get_sync_engine, get_sync_session_factory
from app.security.rate_limit import rate_limiter
from app.services.auth_consent import REQUIRED_AT_REGISTRATION
from app.services.forms.fill.engine import extract_static_text
from app.services.forms.fill.generation_gates import inferred_form_kind, pdf_is_synthetic_underlay
from app.services.forms.fill.underlay import PHOTO_BOX_LABEL, WORKSHEET_BANNER, WORKSHEET_MARKER
from app.services.forms.official_form_acts import OFFICIAL_FORM_ACTS
from app.settings import get_settings


def _clear() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    get_sync_engine.cache_clear()
    get_sync_session_factory.cache_clear()


def _client(tmp_path: Path) -> TestClient:
    data = tmp_path / "data"
    data.mkdir()
    apply_desktop_env(data_dir=data, instance_token="ws-token")
    migrate_sqlite(data)
    _clear()
    from app.main import create_app

    return TestClient(create_app())


def _login(client: TestClient) -> None:
    rate_limiter._events.clear()
    store = client.app.state.auth_store
    accepts = []
    for cid in REQUIRED_AT_REGISTRATION:
        doc = store.active_legal(cid)
        assert doc
        accepts.append(
            {
                "consent_id": doc.consent_id,
                "consent_version": doc.consent_version,
                "content_hash": doc.content_hash,
            },
        )
    email = "ws-user@example.com"
    password = "longpassword1"
    login = client.post("/auth/login", json={"email": email, "password": password})
    if login.status_code == 200:
        return
    registered = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": "Иван Тестов",
            "locale": "ru-RU",
            "accepts": accepts,
        },
    )
    assert registered.status_code == 200, registered.text
    token = registered.json().get("verification_token_dev")
    assert token
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text


def test_official_act_urls_are_allowlisted() -> None:
    for spec in OFFICIAL_FORM_ACTS.values():
        url = spec["official_url"]
        assert url.startswith("https://")
        host = url.split("/")[2]
        assert host in {"publication.pravo.gov.ru", "pravo.gov.ru"}
        assert "consultant" not in url
        assert "garant" not in url


def test_government_cards_have_official_url_and_worksheet(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        cards = client.get("/forms").json()
        gov = [c for c in cards if c["form_kind"] == "government_form"]
        assert len(gov) == 7
        for card in gov:
            assert card["fill_ready"] is False
            assert card["worksheet_ready"] is True
            assert card["official_url"]
            assert card["act_title"]
            pkg = client.get(f"/forms/fill/by-catalog/{card['id']}").json()
            assert pkg["available"] is False
            assert pkg["worksheet"]["available"] is True
            assert pkg["worksheet"]["sections"]
            ver = client.app.state.form_fill.versions[__import__("uuid").UUID(pkg["worksheet"]["version"]["id"])]
            text = "\n".join(extract_static_text(ver.original_pdf))
            assert inferred_form_kind(ver.slug) == "service_worksheet"
            assert WORKSHEET_BANNER not in text
            assert "НЕ БЛАНК ГОСОРГАНА" not in text
            assert WORKSHEET_MARKER in ver.original_pdf
            assert not pdf_is_synthetic_underlay(ver.original_pdf)


def test_worksheet_generate_is_not_government_blank(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        arrival = next(c for c in client.get("/forms").json() if c["slug"] == "mvd.arrival_notice.app4")
        pkg = client.get(f"/forms/fill/by-catalog/{arrival['id']}").json()
        version_id = pkg["worksheet"]["version"]["id"]
        answers = {
            "last_name": "Иванов",
            "first_name": "Иван",
            "citizenship": "Республика Узбекистан",
            "identity_doc": "Паспорт AA 7482915",
            "stay_address": "Москва",
            "host_kind": "физическое лицо",
            "host_name": "Петров П П",
        }
        preview = client.post("/forms/fill/preview", json={"form_version_id": version_id, "answers": answers})
        assert preview.status_code == 200, preview.text
        assert preview.json()["ok"] is True
        gen = client.post(
            "/forms/fill/generate",
            json={"form_version_id": version_id, "answers": answers, "catalog_form_id": arrival["id"]},
        )
        assert gen.status_code == 200, gen.text
        pdf = client.get(f"/forms/fill/generated/{gen.json()['generated_id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        body = "\n".join(extract_static_text(pdf.content))
        assert WORKSHEET_BANNER not in body
        assert "НЕ БЛАНК ГОСОРГАНА" not in body
        assert "Docly" in body
        assert b"source:test-synthetic-underlay" not in pdf.content
        disp = pdf.headers.get("content-disposition") or ""
        assert "pamyatka-vizit" not in disp
        assert "uvedomlenie-pribytie" in disp or "svedeniya" in disp


def test_patent_pdf_has_photo_organ_and_rejects_rf(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        patent = next(c for c in client.get("/forms").json() if c["slug"] == "mvd.patent.application")
        assert "679" in (patent.get("warning") or "") + (patent.get("act_title") or "")
        assert "31.10.2022" in (patent.get("warning") or "") + (patent.get("edition") or "") + (
            patent.get("act_title") or ""
        )
        pkg = client.get(f"/forms/fill/by-catalog/{patent['id']}").json()
        version_id = pkg["worksheet"]["version"]["id"]
        schema = pkg["worksheet"]["field_schema"]
        assert "territorial_organ" in schema
        assert "petition" in schema
        assert "migration_card_series" in schema
        under = client.get(pkg["worksheet"]["underlay_url"])
        assert under.status_code == 200
        text = "\n".join(extract_static_text(under.content))
        assert PHOTO_BOX_LABEL.split()[0] in text or "30" in text
        bad = client.post(
            "/forms/fill/preview",
            json={
                "form_version_id": version_id,
                "answers": {
                    "territorial_organ": "ГУ МВД России по г. Москве",
                    "petition": "Прошу оформить патент на осуществление трудовой деятельности в Российской Федерации",
                    "last_name": "Иванов",
                    "first_name": "Иван",
                    "citizenship": "Российская Федерация",
                    "identity_doc_kind": "Пасспорт",
                    "identity_doc_series": "AA",
                    "identity_doc_number": "1234567",
                    "migration_card_series": "2518",
                    "migration_card_number": "1234567890",
                    "profession": "Журналист",
                    "work_region": "Москва",
                },
            },
        )
        assert bad.status_code == 200
        assert bad.json()["ok"] is False
        codes = {i["code"] for i in bad.json()["issues"]}
        assert "citizenship_rf" in codes
        assert "dummy_value" in codes or "migration_card_format" in codes
        good = {
            "territorial_organ": "ГУ МВД России по г. Москве",
            "petition": "Прошу оформить патент на осуществление трудовой деятельности в Российской Федерации",
            "last_name": "Иванов",
            "first_name": "Иван",
            "citizenship": "Республика Узбекистан",
            "identity_doc_kind": "Паспорт",
            "identity_doc_series": "AA",
            "identity_doc_number": "7482915",
            "migration_card_series": "2518",
            "migration_card_number": "4829173",
            "profession": "Журналист",
            "work_region": "Москва",
            "address_rf": "г. Москва",
        }
        preview = client.post("/forms/fill/preview", json={"form_version_id": version_id, "answers": good})
        assert preview.status_code == 200, preview.text
        assert preview.json()["ok"] is True
        gen = client.post(
            "/forms/fill/generate",
            json={"form_version_id": version_id, "answers": good, "catalog_form_id": patent["id"]},
        )
        assert gen.status_code == 200, gen.text
        pdf = client.get(f"/forms/fill/generated/{gen.json()['generated_id']}/pdf")
        assert pdf.status_code == 200
        disp = pdf.headers.get("content-disposition") or ""
        assert "zayavlenie-patent" in disp
        assert "pamyatka-vizit" not in disp


def test_stay_extension_is_not_a_unified_blank(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        card = next(c for c in client.get("/forms").json() if c["slug"] == "mvd.stay_extension")
        assert card["unified_official_form"] is False
        assert card["fill_ready"] is False
        assert "единого бланка" in (card["warning"] or "").lower() or "единый бланк" in (card["edition"] or "").lower()


def test_work_notification_follows_form1_annex7(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        card = next(c for c in client.get("/forms").json() if c["slug"] == "mvd.work_notification")
        blob = (card.get("warning") or "") + (card.get("act_title") or "")
        assert "536" in blob
        assert "552" in blob
        assert card["fill_ready"] is False
        assert "заключение/расторжение" not in (card.get("title") or "").lower()
        pkg = client.get(f"/forms/fill/by-catalog/{card['id']}").json()
        schema = pkg["worksheet"]["field_schema"]
        section_ids = [s["id"] for s in pkg["worksheet"]["sections"]]
        assert section_ids[:5] == ["head", "employer", "worker", "permit", "sign"]
        for key in (
            "territorial_organ",
            "employer_status",
            "okved",
            "employer_full_name",
            "employer_inn",
            "last_name",
            "first_name",
            "citizenship",
            "identity_doc_series",
            "permit_kind",
            "profession",
            "contract_kind",
            "contract_date",
            "work_address",
            "signatory_title_name",
        ):
            assert key in schema, key
        assert "employer_name" not in schema
        assert "worker_fio" not in schema
        assert "notification_kind" not in schema
        under = client.get(pkg["worksheet"]["underlay_url"])
        assert under.status_code == 200
        text = "\n".join(extract_static_text(under.content))
        assert "536" in text
        assert "552" in text
        assert "ФОРМА 1" in text or "Форма 1" in text
        assert "Приложение" in text
        assert WORKSHEET_BANNER not in text
        version_id = pkg["worksheet"]["version"]["id"]
        answers = {
            "territorial_organ": "МВД по Республике Мордовия",
            "employer_status": "юридическое лицо",
            "okved": "62.01",
            "employer_full_name": "Общество с ограниченной ответственностью Пример",
            "employer_reg_number": "1127746123456",
            "employer_inn": "7701234567",
            "employer_address": "г. Саранск, ул. Примерная, д. 1",
            "employer_phone": "83421234567",
            "last_name": "Karimov",
            "first_name": "Ali",
            "patronymic": "",
            "citizenship": "Республика Узбекистан",
            "birth_date": "12.03.1994",
            "identity_doc_kind": "Паспорт",
            "identity_doc_series": "AA",
            "identity_doc_number": "7482915",
            "identity_doc_issued_date": "01.02.2020",
            "identity_doc_issuer": "МВД",
            "permit_kind": "патент",
            "permit_series": "77",
            "permit_number": "1827364",
            "profession": "каменщик",
            "contract_kind": "трудовой договор",
            "contract_date": "01.08.2026",
            "work_address": "г. Саранск, ул. Строителей, д. 10",
            "signatory_title_name": "директор Иванов И.И.",
        }
        preview = client.post("/forms/fill/preview", json={"form_version_id": version_id, "answers": answers})
        assert preview.status_code == 200, preview.text
        assert preview.json()["ok"] is True, preview.text
        gen = client.post(
            "/forms/fill/generate",
            json={"form_version_id": version_id, "answers": answers, "catalog_form_id": card["id"]},
        )
        assert gen.status_code == 200, gen.text
        pdf = client.get(f"/forms/fill/generated/{gen.json()['generated_id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        body = "\n".join(extract_static_text(pdf.content))
        assert "536" in body
        assert WORKSHEET_BANNER not in body
        disp = pdf.headers.get("content-disposition") or ""
        assert "uvedomlenie-trud" in disp
