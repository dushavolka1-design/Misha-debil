"""User-entered values must be checked — not accepted as-is."""

from app.services.forms.fill.answer_checks import PETITION_PATENT, check_answers, normalize_answers


def test_patent_rejects_rf_citizenship_typo_and_dummy_card() -> None:
    issues = check_answers(
        "worksheet.mvd.patent.application",
        {
            "citizenship": "Российская Федерация",
            "identity_doc_kind": "Пасспорт",
            "migration_card_number": "1234567890",
            "petition": "хочу патент",
        },
        {
            "citizenship": {"label": "Гражданство"},
        },
    )
    codes = {i.code for i in issues}
    assert "citizenship_rf" in codes
    assert "spelling" in codes
    assert "dummy_value" in codes
    assert "petition_wording" in codes


def test_patent_accepts_foreign_passport_and_real_card() -> None:
    issues = check_answers(
        "mvd.patent.application",
        {
            "citizenship": "Республика Узбекистан",
            "identity_doc_kind": "Паспорт",
            "identity_doc_series": "AA",
            "identity_doc_number": "7482915",
            "migration_card_series": "2518",
            "migration_card_number": "4829173",
            "petition": "Прошу оформить патент на осуществление трудовой деятельности в Российской Федерации",
        },
        {"citizenship": {"label": "Гражданство"}},
    )
    assert [i for i in issues if i.severity == "error"] == []


def test_normalize_fixes_passport_and_patent_petition() -> None:
    fixed, corrections = normalize_answers(
        "worksheet.mvd.patent.application",
        {
            "identity_doc_kind": "Пасспорт",
            "petition": "хочу патент",
            "migration_card_series": "25-18",
        },
    )
    assert fixed["identity_doc_kind"] == "Паспорт"
    assert fixed["petition"] == PETITION_PATENT
    assert fixed["migration_card_series"] == "2518"
    assert {c["field_id"] for c in corrections} >= {"identity_doc_kind", "petition", "migration_card_series"}
    leftover = check_answers(
        "mvd.patent.application",
        {
            **fixed,
            "citizenship": "Республика Узбекистан",
            "identity_doc_series": "AA",
            "identity_doc_number": "7482915",
            "migration_card_number": "4829173",
        },
        {"citizenship": {"label": "Гражданство"}},
    )
    assert [i for i in leftover if i.severity == "error"] == []
