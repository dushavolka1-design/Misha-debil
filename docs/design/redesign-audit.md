# Docly redesign audit — preliminary

Date: 2026-09-06. Base master: `7ab48303efa92b2e52702256dcdd360c9540d273`. Work branch: `astra/docly-modern-redesign-20260906`.

## Scope
Partial static audit, not a complete route/browser/accessibility/performance audit. Inspected shared Shell, registration/login, UI controls/tokens, legal consent specification, auth backend schemas/routes, API client, Storybook configuration and relevant frontend tests. No claim of verified whole-app readiness.

## Route inventory (partial)
Existing directories: `/`, `/auth/register`, `/auth/login`, `/app`, analyzer, upload, compare, jobs, reports, generator, entry-wizard, forms, sources, profile, billing. Dynamic subroutes have not been exhaustively inventoried. Existing Shell primarily groups Analyzer and Generation.

## Findings
- UX-01: credentials, repeated password, optional avatar and all consent controls share one registration screen.
- UX-02: active-document loading failure copy exposes API/CORS details; links can fall back to #.
- UX-03: signup/login lack a synchronous duplicate-submit guard and reliable rejection handling.
- UX-04: signup email/password autocomplete and visibility/Caps Lock support need improvement.
- UX-05: shared apiFetch defaults to retries; auth mutations must explicitly disable retries.
- UX-06: existing required terms, offer and ordinary-PD accepts are separate; marketing is false; medical is absent. Preserve these protections.
- UX-07: current backend requires display_name and supports username login; do not silently replace these contracts with email-only authentication.
- UX-08: inspected backend has verify-email but no resend/reset endpoints. Do not invent working controls.
- UX-09: profile dropdown menu semantics lack a complete keyboard/focus-return implementation.
- UX-10: legacy styles contain hard-coded light surfaces, focus outline suppression and overflow-x:hidden; global dark conversion risks regressions.
- UX-11: legacy token and source-regex tests are brittle. Preserve token assertions; deliberately update tests only for approved flow changes.
- UX-12: full mobile, long-content, source/document-type, WCAG and performance coverage is not yet established.

## Proposed first increment
Scoped auth foundation; PasswordInput and semantic Stepper; staged credentials/consents; existing-client adapters; honest loading/error/uncertain-result states. Preserve profile/avatar and existing legal/source/generation controls. Navigation/dashboard/scenarios remain separate future increments, not fictional routes/data.

## Environment and evidence limits
Git clone failed because github.com could not be resolved in the sandbox. GitHub integration can read/write the review branch, but cannot install Next/backend dependencies locally. Isolated component QA is not a running Next/FastAPI application. See redesign-report.md for actual executed checks and open blockers.
