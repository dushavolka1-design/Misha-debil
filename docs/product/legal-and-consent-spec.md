# Legal and consent specification

Status: stage 4 + stage 12 (full draft package). Aligns with ADR-0005.

Placeholders: see `legal/placeholders.md`. Do not invent owner details or statutory deadlines.

## 1. Document kinds

| consent_id | Required at registration | Notes |
|------------|--------------------------|-------|
| `terms_of_use` | yes | Product use |
| `offer` | yes | Paid features |
| `privacy_policy` | no (linked) | Informational policy |
| `personal_data_processing` | yes | Ordinary PD — **separate** control |
| `marketing` | no | Optional, default unchecked |
| `cookies_notice` | no | Cookie notice/settings |
| `payment_recurring` | no | Required in payment flow |
| `special_categories.medical` | **never at registration** | Gate before medical upload |

Ordinary PD consent must not be bundled with offer/terms. Special medical consent: `FINAL_CONSENT_MECHANISM_NEEDS_LEGAL_REVIEW`.

## 2. Versioned rules

Published versions are immutable (`content_hash`, `effective_at`, `publication_status`). Corrections require a new version.

Production gate (`dar.legal_gate` + `LEGAL_ROOT`): fail if placeholders remain, manifest not `approved`, lawyer/privacy_officer not approved, or effective published version missing.

## 3. ConsentEvent

Append-only evidence (`consent_evidence.v1`). Proof returns exact canonical text matching `content_hash`.

## 4. Registration UX

Unchecked terms, offer, separate PD; optional marketing unchecked; link to privacy policy. Backend validates versions/hashes.

## 5–8. Medical gate, material change, withdrawal, auth

Unchanged from stage 4: medical never at signup; export/delete always allowed; Argon2id sessions; anti-enumeration.

## 9. Billing

Separate `payment_recurring` consent. Cancel auto-renew visible in billing UI without requiring support contact. Disclaimer on reports/export does not waive mandatory consumer liability.

## 10. Acceptance tests

No pre-checked boxes; PD separate; marketing optional; register without consents → 400; proof by hash; production gate fails on drafts; billing cancel visible.
