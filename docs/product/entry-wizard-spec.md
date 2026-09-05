# Entry / stay document wizard

- Этап 9. Rule-driven master — not a universal static list.
- Related: UC-ENTRY-WIZARD, ADR-0004, official-source-policy.

## Principles

1. Outcomes come only from versioned decision rules with official source bindings and validity intervals.
2. Unknown citizenship / unsupported visa regime / missing approved source → `unknown_case` or `needs_review`, never invented steps.
3. Do not promise border admission or acceptance of applications.
4. Draft questionnaire saved only after explicit consent.
5. Fees shown only from approved source snapshot with effective date; otherwise ask user to check the official resource.
6. Result snapshot records which rule pack edition fired; refresh re-evaluates against current approved sources.

## Questionnaire (minimal sensitive data)

citizenship / stateless, second citizenship (yes/no + optional code), age band, visa_regime_id (from approved catalog only),
purpose, planned stay duration, planned entry date, work/study/family/tourism flags as purpose enum,
eaeu_member, invitation, host_type, region_code (optional), special_statuses[].

## Result stages

`before_trip` | `at_border` | `after_entry` | `work_study` | `extension_change` | `medical_dactylo`

Each step: actor, prepare, deadline + calculation explanation, where, official source, as_of, exceptions, needs_review, activated_by answers.
