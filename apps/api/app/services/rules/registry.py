from __future__ import annotations

"""Versioned general-purpose rule registry. Not universal legal advice."""

from app.services.rules.types import ResultKind, RuleDef, RuleTestCase, Severity, Uncertainty

GENERAL = (
    "contract.other",
    "contract.lease",
    "contract.sale_purchase",
    "contract.services",
    "contract.nda",
    "user.doc.general",
)


def _tc(case_id: str, facts: list, expect: bool, unc: Uncertainty | None = None, note: str = "") -> RuleTestCase:
    return RuleTestCase(case_id=case_id, facts=facts, expect_trigger=expect, expect_uncertainty=unc, note=note)


RULES: tuple[RuleDef, ...] = (
    RuleDef(
        rule_id="party.requisites_incomplete",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("party.name",),
        severity=Severity.MEDIUM,
        severity_rationale="Incomplete party details need human confirmation before relying on the extract.",
        official_sources=("SRC.PARTY.REQUISITES.v1",),
        message_template="У стороны «{name}» не хватает согласованных реквизитов (роль/идентификатор/адрес).",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        description="Empty/inconsistent party requisites",
        test_cases=(
            _tc(
                "fp_complete",
                [
                    {"entity_type": "party.name", "raw_text": "ООО А", "normalized_value": "ООО А"},
                    {"entity_type": "party.role", "raw_text": "арендодатель"},
                    {"entity_type": "party.identifier", "raw_text": "ИНН 7707083893"},
                ],
                False,
            ),
            _tc("fn_missing_role", [{"entity_type": "party.name", "raw_text": "ООО А"}], True),
        ),
    ),
    RuleDef(
        rule_id="conflict.names_roles",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("party.name", "party.role"),
        severity=Severity.HIGH,
        severity_rationale="Conflicting party names/roles across facts warrant priority review.",
        official_sources=("SRC.CONSISTENCY.v1",),
        message_template="Обнаружен конфликт имён или ролей сторон в извлечённых фактах.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.STRUCTURAL_CONFLICT,
        test_cases=(
            _tc(
                "dup_same",
                [
                    {"entity_type": "party.name", "raw_text": "ООО А"},
                    {"entity_type": "party.name", "raw_text": "ООО А"},
                ],
                False,
            ),
            _tc(
                "conflict",
                [
                    {"entity_type": "party.role", "raw_text": "покупатель", "citation": {"page": 1}},
                    {
                        "entity_type": "party.role",
                        "raw_text": "продавец",
                        "citation": {"page": 1},
                        "same_party_hint": "A",
                    },
                ],
                True,
                note="contradictory evidence",
            ),
        ),
    ),
    RuleDef(
        rule_id="conflict.dates_amounts_currency",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("amount.value",),
        severity=Severity.HIGH,
        severity_rationale="Numeric/currency conflicts are structural and easy to miss manually.",
        official_sources=("SRC.CONSISTENCY.v1",),
        message_template="Конфликт дат, сумм или валют между фактами документа.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.STRUCTURAL_CONFLICT,
        test_cases=(
            _tc(
                "same_amount",
                [
                    {"entity_type": "amount.value", "normalized_value": {"amount": "1000", "currency": "RUB"}},
                    {"entity_type": "amount.value", "normalized_value": {"amount": "1000", "currency": "RUB"}},
                ],
                False,
            ),
            _tc(
                "currency_conflict",
                [
                    {"entity_type": "amount.value", "normalized_value": {"amount": "1000", "currency": "RUB"}},
                    {"entity_type": "amount.value", "normalized_value": {"amount": "1000", "currency": "USD"}},
                ],
                True,
            ),
        ),
    ),
    RuleDef(
        rule_id="date.end_before_start",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("doc.date.effective", "doc.date.end"),
        severity=Severity.HIGH,
        severity_rationale="End-before-start is an objective structural inconsistency.",
        official_sources=("SRC.CONSISTENCY.v1",),
        message_template="Дата окончания ({end}) раньше даты начала ({start}).",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.STRUCTURAL_CONFLICT,
        test_cases=(
            _tc(
                "ok_order",
                [
                    {"entity_type": "doc.date.effective", "normalized_value": "2026-01-01"},
                    {"entity_type": "doc.date.end", "normalized_value": "2026-12-31"},
                ],
                False,
            ),
            _tc(
                "bad_order",
                [
                    {"entity_type": "doc.date.effective", "normalized_value": "2026-12-31"},
                    {"entity_type": "doc.date.end", "normalized_value": "2026-01-01"},
                ],
                True,
            ),
            _tc(
                "missing",
                [{"entity_type": "doc.date.effective", "normalized_value": "2026-01-01"}],
                False,
                Uncertainty.INSUFFICIENT_DATA,
                "missing context",
            ),
        ),
    ),
    RuleDef(
        rule_id="amount.digits_vs_words",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("amount.value",),
        severity=Severity.MEDIUM,
        severity_rationale="Digits vs words mismatch is a common drafting inconsistency.",
        official_sources=("SRC.CONSISTENCY.v1",),
        message_template="Сумма цифрами и прописью различаются: «{digits}» vs «{words}».",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.STRUCTURAL_CONFLICT,
        test_cases=(
            _tc(
                "mismatch",
                [
                    {
                        "entity_type": "amount.value",
                        "raw_text": "1000",
                        "normalized_value": {"amount": "1000", "currency": "RUB"},
                        "meta": {"words": "две тысячи"},
                    },
                    {"entity_type": "amount.words", "raw_text": "две тысячи", "normalized_value": "2000"},
                ],
                True,
            ),
        ),
    ),
    RuleDef(
        rule_id="ref.missing_annex_or_clause",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("annex.ref",),
        severity=Severity.MEDIUM,
        severity_rationale="Broken internal references need confirmation against attachments.",
        official_sources=("SRC.STRUCTURE.v1",),
        message_template="Есть ссылка на приложение/пункт «{ref}», которого нет среди извлечённых вложений.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        test_cases=(
            _tc(
                "missing_annex",
                [
                    {"entity_type": "reference.ref", "raw_text": "Приложение №2"},
                    {"entity_type": "annex.ref", "raw_text": "Приложение №1"},
                ],
                True,
            ),
            _tc(
                "present",
                [
                    {"entity_type": "reference.ref", "raw_text": "Приложение №1"},
                    {"entity_type": "annex.ref", "raw_text": "Приложение №1"},
                ],
                False,
            ),
        ),
    ),
    RuleDef(
        rule_id="obligation.missing_deadline_or_owner",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("obligation.summary",),
        severity=Severity.MEDIUM,
        severity_rationale="Obligations without deadline/owner are incomplete for operational review.",
        official_sources=("SRC.OBLIGATION.v1",),
        message_template="Обязанность без явного срока и/или ответственной стороны: «{summary}».",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        test_cases=(
            _tc("bare", [{"entity_type": "obligation.summary", "raw_text": "Обеспечить доступ", "meta": {}}], True),
        ),
    ),
    RuleDef(
        rule_id="termination.asymmetric_rights",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("termination.clause_ref",),
        severity=Severity.MEDIUM,
        severity_rationale="Asymmetry is a review flag, not a legality verdict.",
        official_sources=("SRC.TERMINATION.v1",),
        message_template="Права расторжения выглядят несимметричными между сторонами — требуется ручная проверка формулировок.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        test_cases=(
            _tc(
                "asym",
                [
                    {
                        "entity_type": "termination.clause_ref",
                        "raw_text": "только Арендодатель вправе расторгнуть",
                        "meta": {"asymmetric": True},
                    }
                ],
                True,
            ),
        ),
    ),
    RuleDef(
        rule_id="penalty.unclear_base_or_cap",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("penalty.clause",),
        severity=Severity.MEDIUM,
        severity_rationale="Unclear penalty base/cap needs human reading of the clause.",
        official_sources=("SRC.PENALTY.v1",),
        message_template="Штраф/пеня без понятной базы расчёта или предела: «{clause}».",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        test_cases=(
            _tc(
                "unclear",
                [
                    {
                        "entity_type": "penalty.clause",
                        "raw_text": "штраф по усмотрению",
                        "meta": {"base": None, "cap": None},
                    }
                ],
                True,
            ),
            _tc(
                "clear",
                [
                    {
                        "entity_type": "penalty.clause",
                        "raw_text": "0.1% в день, не более 10%",
                        "meta": {"base": "0.1%/day", "cap": "10%"},
                    }
                ],
                False,
            ),
        ),
    ),
    RuleDef(
        rule_id="renewal.auto_and_opt_out",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("renewal.clause_ref",),
        severity=Severity.LOW,
        severity_rationale="Auto-renewal windows are easy to miss operationally.",
        official_sources=("SRC.RENEWAL.v1",),
        message_template="Обнаружены автопродление и/или окно отказа — проверьте сроки уведомления.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.OBSERVED_TEXT,
        test_cases=(
            _tc(
                "auto",
                [{"entity_type": "renewal.clause_ref", "raw_text": "автоматически продлевается, отказ за 30 дней"}],
                True,
            ),
        ),
    ),
    RuleDef(
        rule_id="unilateral.terms_change",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("right.summary",),
        severity=Severity.MEDIUM,
        severity_rationale="Unilateral change clauses deserve explicit human attention.",
        official_sources=("SRC.CHANGE.v1",),
        message_template="Есть формулировка одностороннего изменения условий — вопрос для проверки.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.REVIEW_QUESTION,
        test_cases=(
            _tc(
                "uni",
                [
                    {
                        "entity_type": "right.summary",
                        "raw_text": "Исполнитель вправе в одностороннем порядке изменять тарифы",
                    }
                ],
                True,
            ),
        ),
    ),
    RuleDef(
        rule_id="pd.third_party_transfer",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("personal_data.clause",),
        severity=Severity.HIGH,
        severity_rationale="PD transfer clauses are high-priority for privacy review (not a legality verdict).",
        official_sources=("SRC.PD.152FZ.v1",),
        message_template="Обнаружена передача ПД / третьим лицам — сверьте с согласиями и политикой.",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.NORMATIVE_CLAIM,
        test_cases=(_tc("pd", [{"entity_type": "personal_data.clause", "raw_text": "передача третьим лицам"}], True),),
    ),
    RuleDef(
        rule_id="dispute.jurisdiction_governing_law",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("dispute.jurisdiction",),
        severity=Severity.LOW,
        severity_rationale="Jurisdiction/governing law should be visible in the report for review.",
        official_sources=("SRC.DISPUTE.v1",),
        message_template="Указаны подсудность/применимое право: «{text}».",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.OBSERVED_TEXT,
        test_cases=(_tc("msk", [{"entity_type": "dispute.jurisdiction", "raw_text": "г. Москва"}], True),),
    ),
    RuleDef(
        rule_id="multifile.version_conflict",
        version="1.0.0",
        applicability=GENERAL,
        required_facts=("doc.title",),
        severity=Severity.HIGH,
        severity_rationale="Conflicting versions across files need explicit reconciliation.",
        official_sources=("SRC.VERSIONING.v1",),
        message_template="Конфликт версий нескольких файлов по ключу «{key}».",
        reviewer="rules_reviewer_demo",
        result_kind=ResultKind.STRUCTURAL_CONFLICT,
        test_cases=(
            _tc(
                "conflict_files",
                [
                    {"entity_type": "doc.title", "raw_text": "v1", "meta": {"file_id": "a", "version_key": "contract"}},
                    {"entity_type": "doc.title", "raw_text": "v2", "meta": {"file_id": "b", "version_key": "contract"}},
                ],
                True,
            ),
        ),
    ),
)


RULES_BY_ID: dict[str, RuleDef] = {r.rule_id: r for r in RULES}
REGISTRY_VERSION = "rules.registry.v1"
