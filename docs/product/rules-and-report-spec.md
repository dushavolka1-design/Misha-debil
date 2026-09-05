# Risks, contradictions, and comparison

- Этап 7. Aligns with taxonomy CheckPack, ADR-0004, FR-13.

## Principles

1. **No universal legal conclusions.** Never emit “договор незаконен/безопасен”.
2. **Severity** = priority for manual review, not a legal qualification.
3. Separate result kinds:
   - `observed_text` — quote found in document
   - `structural_conflict` — arithmetic/structural inconsistency
   - `review_question` — potential question for human check
   - `normative_claim` — statement tied to an official source snapshot
4. Missing required facts → `uncertain` / `needs_review`, not a hard fail claim.
5. Feedback never mutates analysis results automatically.

## Rule registry fields

`rule_id`, `version`, `applicability` (document_types), `required_facts`, `severity`, `severity_rationale`,
`official_sources`, `message_template`, `reviewer`, `test_cases`.

## Compare

Matches parties, section hierarchy, semantic clauses; emits added/removed/changed with **both** citations.
LLM comparator is tenant/user-scoped and refuses prompt injection / cross-user context.
