from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.entry.deadlines import DeadlineKind, calculate_deadline
from app.services.entry.engine import EntryError, EntryWizardService, Questionnaire
from app.services.entry.pack import APPROVED_VISA_REGIMES, PACK_VERSION
from app.services.sources.fetcher import FakeFetchScript
from app.services.sources.registry import FetchResult, SourceRegistry
from app.services.sources.url_policy import load_allowlist

ALLOWLIST = str(Path(__file__).resolve().parents[3] / "sources" / "allowlist.json")


def _approve_all(reg: SourceRegistry) -> None:
    reg.seed_from_allowlist()
    responses = {}
    for src in reg.sources.values():
        responses[src.official_url] = FetchResult(
            final_url=src.official_url,
            status_code=200,
            headers={"content-type": "text/html", "etag": "1"},
            body=f"<html>{src.host} official</html>".encode(),
            redirect_chain=[src.official_url],
        )
    reg.fetch_fn = FakeFetchScript(responses)
    for src in list(reg.sources.values()):
        snap = reg.fetch_and_parse(src.id)
        reg.approve(
            snap.id,
            actor="reviewer@test",
            comment="seed approve for tests",
            valid_from=date(2024, 1, 1),
            act_title=f"Meta {src.host}",
        )


@pytest.fixture()
def wizard() -> EntryWizardService:
    reg = SourceRegistry(allowlist=load_allowlist(ALLOWLIST))
    _approve_all(reg)
    return EntryWizardService(reg)


def test_no_universal_list_unknown_citizenship(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(citizenship="unknown", visa_regime_id="visa_free_short", purpose="tourism", draft_consent=True),
    )
    assert snap.unknown_case is True
    assert "entry.unknown_citizenship" in snap.activated_rule_ids
    # Must not invent visa_free short visit list for unknown citizenship
    assert "entry.visa_free.short_visit" not in snap.activated_rule_ids
    assert all(
        s.outcome == "unknown_case" or s.rule_id == "entry.unknown_citizenship"
        for st in snap.stages.values()
        for s in st
    )


def test_visa_required_and_visa_free_tables(wizard: EntryWizardService) -> None:
    visa = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            visa_regime_id="visa_required",
            purpose="tourism",
            planned_entry_date=date(2026, 9, 1),
            draft_consent=True,
        ),
    )
    assert "entry.visa_required.docs" in visa.activated_rule_ids
    assert "entry.visa_free.short_visit" not in visa.activated_rule_ids

    vf = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            visa_regime_id="visa_free_short",
            purpose="tourism",
            planned_stay_days=30,
            planned_entry_date=date(2026, 9, 1),
            draft_consent=True,
        ),
    )
    assert "entry.visa_free.short_visit" in vf.activated_rule_ids
    assert "entry.visa_required.docs" not in vf.activated_rule_ids


def test_eaeu_work_study_minor_short_visit(wizard: EntryWizardService) -> None:
    eaeu = wizard.evaluate(
        Questionnaire(
            citizenship="AM",
            eaeu_member=True,
            visa_regime_id="eaeu",
            purpose="tourism",
            planned_entry_date=date(2026, 5, 1),
            draft_consent=True,
        ),
    )
    assert "entry.eaeu.movement" in eaeu.activated_rule_ids

    work = wizard.evaluate(
        Questionnaire(citizenship="ZZ", purpose="work", visa_regime_id="visa_required", draft_consent=True),
    )
    assert "entry.work.permit_check" in work.activated_rule_ids
    assert work.stages["work_study"]

    study = wizard.evaluate(
        Questionnaire(citizenship="ZZ", purpose="study", visa_regime_id="visa_required", draft_consent=True),
    )
    assert "entry.study.enrollment" in study.activated_rule_ids

    minor = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            age_band="minor",
            visa_regime_id="visa_free_short",
            purpose="tourism",
            planned_stay_days=14,
            draft_consent=True,
        ),
    )
    assert "entry.minor.guardian" in minor.activated_rule_ids


def test_each_step_has_source_and_applicability(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            visa_regime_id="visa_required",
            purpose="work",
            planned_entry_date=date(2026, 8, 1),
            draft_consent=True,
        ),
    )
    for steps in snap.stages.values():
        for s in steps:
            assert s.official_sources
            assert s.as_of
            assert s.activated_by
            assert "допуск" not in s.prepare.lower() or "не" in s.prepare.lower()


def test_deadline_not_naive_number() -> None:
    d1 = calculate_deadline("business_days:7:from_entry", anchor=date(2026, 8, 3), timezone="Europe/Moscow")
    assert d1.kind == DeadlineKind.BUSINESS_DAYS
    assert d1.absolute_date is not None
    assert "рабочих" in d1.explanation.lower() or "business" in d1.explanation.lower() or "пн" in d1.explanation

    d2 = calculate_deadline("region_dependent", anchor=date(2026, 1, 1), region_code="77")
    assert d2.needs_review and d2.absolute_date is None

    d3 = calculate_deadline("treaty_dependent", anchor=None)
    assert d3.kind == DeadlineKind.TREATY_DEPENDENT


def test_draft_requires_consent(wizard: EntryWizardService) -> None:
    with pytest.raises(EntryError) as ei:
        wizard.save_draft(Questionnaire(citizenship="ZZ", draft_consent=False), user_id=None)
    assert ei.value.code == "consent_required"
    rec = wizard.save_draft(Questionnaire(citizenship="ZZ", draft_consent=True), user_id=None)
    assert rec.id


def test_unapproved_visa_regime_rejected(wizard: EntryWizardService) -> None:
    with pytest.raises(EntryError):
        wizard.evaluate(Questionnaire(citizenship="ZZ", visa_regime_id="made_up_regime", draft_consent=True))
    assert "visa_required" in APPROVED_VISA_REGIMES


def test_fee_without_approved_catalog_message(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(citizenship="ZZ", visa_regime_id="visa_required", purpose="tourism", draft_consent=True),
    )
    step = next(s for st in snap.stages.values() for s in st if s.rule_id == "entry.visa_required.docs")
    assert step.fee is not None
    assert step.fee["available"] is False
    assert "официальном" in step.fee["message"]


def test_fee_from_approved_source_when_catalog_present(wizard: EntryWizardService) -> None:
    wizard.fee_catalog["mid-ru"] = {"amount": "N/A", "currency": "RUB", "effective_date": "2024-01-01"}
    snap = wizard.evaluate(
        Questionnaire(citizenship="ZZ", visa_regime_id="visa_required", purpose="tourism", draft_consent=True),
    )
    step = next(s for st in snap.stages.values() for s in st if s.rule_id == "entry.visa_required.docs")
    assert step.fee and step.fee["available"] is True
    assert step.fee["source_snapshot_id"]


def test_snapshot_and_refresh(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(citizenship="KZ", eaeu_member=True, visa_regime_id="eaeu", purpose="tourism", draft_consent=True),
    )
    assert snap.pack_version == PACK_VERSION
    refreshed = wizard.refresh(snap.id)
    assert refreshed.id != snap.id
    assert refreshed.questionnaire["citizenship"] == "KZ"
    assert "entry.eaeu.movement" in refreshed.activated_rule_ids


def test_freshness_blocks_stale_source(wizard: EntryWizardService) -> None:
    # Mark mid-ru latest as stale
    sid = wizard.sources.by_slug["mid-ru"]
    latest = wizard.sources.latest_snapshot(sid)
    assert latest
    latest.link_status = "stale"
    snap = wizard.evaluate(
        Questionnaire(citizenship="ZZ", visa_regime_id="visa_required", purpose="tourism", draft_consent=True),
    )
    assert any(
        "entry.visa_required" in x or x == "entry.visa_required.docs" for x in snap.freshness_blocked_rules
    ) or any(s.freshness_blocked for st in snap.stages.values() for s in st if s.rule_id == "entry.visa_required.docs")


def test_source_conflict_sets_block(wizard: EntryWizardService) -> None:
    sid = wizard.sources.by_slug["mid-ru"]
    src = wizard.sources.sources[sid]
    # New awaiting snapshot with different hash
    approved = wizard.sources.approved_snapshot(sid)
    assert approved
    wizard.sources.fetch_fn = FakeFetchScript(
        {
            src.official_url: FetchResult(
                final_url=src.official_url,
                status_code=200,
                headers={"content-type": "text/html", "etag": "2"},
                body=b"<html>changed content for conflict</html>",
                redirect_chain=[src.official_url],
            ),
        },
    )
    wizard.sources.fetch_and_parse(sid)
    snap = wizard.evaluate(
        Questionnaire(citizenship="ZZ", visa_regime_id="visa_required", draft_consent=True),
    )
    assert "source_conflict" in snap.freshness_blocked_rules


def test_explains_activated_answers(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            purpose="family",
            invitation=True,
            host_type="individual",
            visa_regime_id="visa_required",
            draft_consent=True,
        ),
    )
    family = next(s for st in snap.stages.values() for s in st if s.rule_id == "entry.family.host")
    assert family.activated_by.get("purpose") == "family"
    assert family.activated_by.get("invitation") is True


def test_disclaimer_no_admission_promise(wizard: EntryWizardService) -> None:
    snap = wizard.evaluate(
        Questionnaire(
            citizenship="ZZ",
            visa_regime_id="visa_free_short",
            purpose="tourism",
            planned_stay_days=10,
            draft_consent=True,
        )
    )
    assert "не обещает допуск" in snap.disclaimer.lower() or "не обещает" in snap.disclaimer.lower()
