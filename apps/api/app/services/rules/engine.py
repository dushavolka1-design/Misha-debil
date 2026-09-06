from __future__ import annotations

import re
from typing import Any

from app.services.rules.registry import REGISTRY_VERSION, RULES, RULES_BY_ID
from app.services.rules.types import (
    ResultKind,
    RuleDef,
    RuleHit,
    Severity,
    Uncertainty,
    assert_safe_message,
)


def _facts_of(facts: list[dict[str, Any]], entity_type: str) -> list[dict[str, Any]]:
    return [f for f in facts if f.get("entity_type") == entity_type]


def _citation(f: dict[str, Any]) -> dict[str, Any] | None:
    c = f.get("citation")
    return c if isinstance(c, dict) else None


def _missing_required(rule: RuleDef, facts: list[dict[str, Any]]) -> list[str]:
    present = {f.get("entity_type") for f in facts}
    return [r for r in rule.required_facts if r not in present]


def _hit(
    rule: RuleDef,
    message: str,
    *,
    uncertainty: Uncertainty = Uncertainty.OK,
    citations: list[dict] | None = None,
    basis: list[str] | None = None,
) -> RuleHit:
    assert_safe_message(message)
    return RuleHit(
        rule_id=rule.rule_id,
        rule_version=rule.version,
        result_kind=rule.result_kind,
        severity=rule.severity,
        severity_rationale=rule.severity_rationale,
        message=message,
        uncertainty=uncertainty,
        citations=citations or [],
        basis_fact_keys=basis or [],
        official_sources=list(rule.official_sources),
    )


def eval_party_requisites(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    names = _facts_of(facts, "party.name")
    if not names:
        return [
            _hit(
                rule,
                "Не удалось проверить реквизиты сторон: нет извлечённых имён.",
                uncertainty=Uncertainty.INSUFFICIENT_DATA,
            ),
        ]
    roles = _facts_of(facts, "party.role")
    ids = _facts_of(facts, "party.identifier")
    addrs = _facts_of(facts, "party.address")
    hits = []
    for n in names:
        if not roles or (not ids and not addrs):
            hits.append(
                _hit(
                    rule,
                    rule.message_template.format(name=n.get("raw_text", "?")),
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(n)] if c],
                    basis=["party.name"],
                ),
            )
    return hits


def eval_conflict_names_roles(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    # Explicit contradictory evidence via meta
    for f in facts:
        if f.get("meta", {}).get("contradicts"):
            hits.append(_hit(rule, rule.message_template, basis=["party.name", "party.role"]))
            break
    roles = _facts_of(facts, "party.role")
    for i, f in enumerate(roles):
        if f.get("same_party_hint"):
            others = [x for j, x in enumerate(roles) if j != i]
            if others and others[0].get("raw_text", "").lower() != f.get("raw_text", "").lower():
                hits.append(
                    _hit(
                        rule,
                        rule.message_template,
                        citations=[c for c in [_citation(f), _citation(others[0])] if c],
                        basis=["party.role"],
                    ),
                )
                break
    return hits


def eval_conflict_amounts(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    amounts = _facts_of(facts, "amount.value")
    if len(amounts) < 2:
        return []
    currencies = set()
    values = set()
    citations = []
    for a in amounts:
        nv = a.get("normalized_value") or {}
        if isinstance(nv, dict):
            if nv.get("currency"):
                currencies.add(str(nv["currency"]).upper())
            if nv.get("amount"):
                values.add(str(nv["amount"]))
        c = _citation(a)
        if c:
            citations.append(c)
    if len(currencies) > 1 or len(values) > 1:
        return [_hit(rule, rule.message_template, citations=citations, basis=["amount.value"])]
    return []


def eval_end_before_start(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    starts = _facts_of(facts, "doc.date.effective")
    ends = _facts_of(facts, "doc.date.end")
    if not starts or not ends:
        return [
            _hit(
                rule,
                "Недостаточно дат начала/окончания для проверки порядка.",
                uncertainty=Uncertainty.INSUFFICIENT_DATA,
            ),
        ]
    start = starts[0].get("normalized_value") or starts[0].get("raw_text")
    end = ends[0].get("normalized_value") or ends[0].get("raw_text")
    if isinstance(start, str) and isinstance(end, str) and start > end:
        return [
            _hit(
                rule,
                rule.message_template.format(start=start, end=end),
                citations=[c for c in [_citation(starts[0]), _citation(ends[0])] if c],
                basis=["doc.date.effective", "doc.date.end"],
            ),
        ]
    return []


def eval_digits_vs_words(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    amounts = _facts_of(facts, "amount.value")
    words = _facts_of(facts, "amount.words")
    hits = []
    for a in amounts:
        meta = a.get("meta") or {}
        if meta.get("words") and a.get("normalized_value"):
            # If companion amount.words present with different normalized
            for w in words:
                wn = str(w.get("normalized_value", ""))
                an = str((a.get("normalized_value") or {}).get("amount", ""))
                if wn and an and wn.replace(" ", "") != an.replace(" ", ""):
                    hits.append(
                        _hit(
                            rule,
                            rule.message_template.format(digits=an, words=w.get("raw_text", wn)),
                            citations=[c for c in [_citation(a), _citation(w)] if c],
                            basis=["amount.value"],
                        ),
                    )
        # Also support words embedded in meta only
        if meta.get("words_value") and a.get("normalized_value"):
            an = str((a.get("normalized_value") or {}).get("amount", ""))
            if str(meta["words_value"]) != an:
                hits.append(
                    _hit(
                        rule,
                        rule.message_template.format(digits=an, words=meta.get("words", "")),
                        citations=[c for c in [_citation(a)] if c],
                        basis=["amount.value"],
                    ),
                )
    return hits


def eval_missing_annex(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    refs = _facts_of(facts, "reference.ref") + [
        f for f in facts if f.get("entity_type") == "annex.ref" and f.get("meta", {}).get("is_reference")
    ]
    # Prefer explicit reference.ref
    refs = _facts_of(facts, "reference.ref")
    annexes = {f.get("raw_text", "").strip().lower() for f in _facts_of(facts, "annex.ref")}
    hits = []
    for r in refs:
        key = r.get("raw_text", "").strip().lower()
        if key and key not in annexes and not any(key in a or a in key for a in annexes):
            hits.append(
                _hit(
                    rule,
                    rule.message_template.format(ref=r.get("raw_text")),
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(r)] if c],
                    basis=["reference.ref", "annex.ref"],
                ),
            )
    return hits


def eval_obligation_incomplete(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for o in _facts_of(facts, "obligation.summary"):
        meta = o.get("meta") or {}
        if not meta.get("deadline") and not meta.get("owner"):
            hits.append(
                _hit(
                    rule,
                    rule.message_template.format(summary=o.get("raw_text", "")[:160]),
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(o)] if c],
                    basis=["obligation.summary"],
                ),
            )
    return hits


def eval_termination_asymmetric(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for t in _facts_of(facts, "termination.clause_ref"):
        text = t.get("raw_text", "")
        meta = t.get("meta") or {}
        if meta.get("asymmetric") or re.search(r"(?i)только\s+\w+\s+вправе\s+расторг", text):
            hits.append(
                _hit(
                    rule,
                    rule.message_template,
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(t)] if c],
                    basis=["termination.clause_ref"],
                ),
            )
    return hits


def eval_penalty_unclear(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for p in _facts_of(facts, "penalty.clause"):
        meta = p.get("meta") or {}
        text = p.get("raw_text", "")
        unclear = (meta.get("base") is None and meta.get("cap") is None) or re.search(
            r"(?i)по усмотрению|на усмотрение",
            text,
        )
        if unclear and not (meta.get("base") and meta.get("cap")):
            hits.append(
                _hit(
                    rule,
                    rule.message_template.format(clause=text[:160]),
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(p)] if c],
                    basis=["penalty.clause"],
                ),
            )
    return hits


def eval_renewal(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for r in _facts_of(facts, "renewal.clause_ref"):
        text = r.get("raw_text", "")
        if re.search(r"(?i)автоматич|продлева|отказ|уведомлен", text):
            hits.append(
                _hit(
                    rule,
                    rule.message_template,
                    citations=[c for c in [_citation(r)] if c],
                    basis=["renewal.clause_ref"],
                ),
            )
    return hits


def eval_unilateral(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for r in _facts_of(facts, "right.summary"):
        if re.search(r"(?i)односторонн", r.get("raw_text", "")):
            hits.append(
                _hit(
                    rule,
                    rule.message_template,
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(r)] if c],
                    basis=["right.summary"],
                ),
            )
    return hits


def eval_pd_transfer(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for p in _facts_of(facts, "personal_data.clause"):
        text = p.get("raw_text", "")
        if re.search(r"(?i)третьим лицам|передача пд|персональн", text):
            hits.append(
                _hit(
                    rule,
                    rule.message_template,
                    uncertainty=Uncertainty.NEEDS_REVIEW,
                    citations=[c for c in [_citation(p)] if c],
                    basis=["personal_data.clause"],
                    # normative claim cites source snapshot ids from rule
                ),
            )
    return hits


def eval_jurisdiction(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    hits = []
    for j in _facts_of(facts, "dispute.jurisdiction"):
        hits.append(
            _hit(
                rule,
                rule.message_template.format(text=j.get("raw_text", "")[:160]),
                citations=[c for c in [_citation(j)] if c],
                basis=["dispute.jurisdiction"],
            ),
        )
    return hits


def eval_multifile_version(rule: RuleDef, facts: list[dict[str, Any]]) -> list[RuleHit]:
    by_key: dict[str, list[dict]] = {}
    for f in _facts_of(facts, "doc.title"):
        meta = f.get("meta") or {}
        key = meta.get("version_key")
        if key:
            by_key.setdefault(str(key), []).append(f)
    hits = []
    for key, group in by_key.items():
        texts = {g.get("raw_text") for g in group}
        files = {(g.get("meta") or {}).get("file_id") for g in group}
        if len(texts) > 1 and len(files) > 1:
            hits.append(
                _hit(
                    rule,
                    rule.message_template.format(key=key),
                    citations=[c for g in group for c in [_citation(g)] if c],
                    basis=["doc.title"],
                ),
            )
    return hits


EVALUATORS = {
    "party.requisites_incomplete": eval_party_requisites,
    "conflict.names_roles": eval_conflict_names_roles,
    "conflict.dates_amounts_currency": eval_conflict_amounts,
    "date.end_before_start": eval_end_before_start,
    "amount.digits_vs_words": eval_digits_vs_words,
    "ref.missing_annex_or_clause": eval_missing_annex,
    "obligation.missing_deadline_or_owner": eval_obligation_incomplete,
    "termination.asymmetric_rights": eval_termination_asymmetric,
    "penalty.unclear_base_or_cap": eval_penalty_unclear,
    "renewal.auto_and_opt_out": eval_renewal,
    "unilateral.terms_change": eval_unilateral,
    "pd.third_party_transfer": eval_pd_transfer,
    "dispute.jurisdiction_governing_law": eval_jurisdiction,
    "multifile.version_conflict": eval_multifile_version,
}


def run_rules(
    facts: list[dict[str, Any]],
    *,
    document_type: str = "contract.other",
) -> list[RuleHit]:
    hits: list[RuleHit] = []
    for rule in RULES:
        if document_type not in rule.applicability and "user.doc.general" not in rule.applicability:
            # still allow general
            if document_type not in rule.applicability:
                continue
        missing = _missing_required(rule, facts)
        # Some rules handle missing internally with insufficient_data
        fn = EVALUATORS.get(rule.rule_id)
        if not fn:
            continue
        rule_hits = fn(rule, facts)
        # If required facts missing and evaluator returned nothing, emit uncertain
        if (
            missing
            and not rule_hits
            and rule.rule_id
            in {
                "date.end_before_start",
                "conflict.dates_amounts_currency",
            }
        ):
            continue
        hits.extend(rule_hits)
    # Final safety: strip any forbidden phrasing
    for h in hits:
        assert_safe_message(h.message)
    return hits


def run_rule_testcases() -> list[dict[str, Any]]:
    """Execute registry embedded test cases; returns failures."""
    failures = []
    for rule in RULES:
        fn = EVALUATORS.get(rule.rule_id)
        if not fn:
            failures.append({"rule_id": rule.rule_id, "error": "no_evaluator"})
            continue
        for tc in rule.test_cases:
            hits = fn(rule, tc.facts)
            triggered = len(hits) > 0 and not all(h.uncertainty == Uncertainty.INSUFFICIENT_DATA for h in hits)
            # For missing-context cases, expect insufficient_data hit or no hard trigger
            if tc.expect_uncertainty == Uncertainty.INSUFFICIENT_DATA:
                ok = any(h.uncertainty == Uncertainty.INSUFFICIENT_DATA for h in hits) or (
                    not tc.expect_trigger and not triggered
                )
                if not ok:
                    failures.append({"rule_id": rule.rule_id, "case": tc.case_id, "expected": "insufficient_data"})
                continue
            if triggered != tc.expect_trigger:
                failures.append(
                    {
                        "rule_id": rule.rule_id,
                        "case": tc.case_id,
                        "expected_trigger": tc.expect_trigger,
                        "got": triggered,
                        "note": tc.note,
                    },
                )
    return failures


def registry_meta() -> dict[str, Any]:
    return {
        "registry_version": REGISTRY_VERSION,
        "rules": [
            {
                "rule_id": r.rule_id,
                "version": r.version,
                "severity": r.severity.value,
                "severity_rationale": r.severity_rationale,
                "result_kind": r.result_kind.value,
                "required_facts": list(r.required_facts),
                "official_sources": list(r.official_sources),
                "reviewer": r.reviewer,
            }
            for r in RULES
        ],
    }
