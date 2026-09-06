# Staging go / no-go report

**Environment:** staging (synthetic data only)  
**Date:** 2026-08-11  
**Verdict: NO-GO** — critical gates open. Do **not** declare production-ready.

Synthetic seed: `infra/staging/synthetic_seed.md`. Compose: `infra/docker-compose.staging.yml`.

---

## Gate snapshot

| Gate | Status | Notes |
|------|--------|-------|
| QG-TRACE | PASS (doc) | Traceability matrix published |
| QG-UNIT | PASS (local) | API pytest suite green in CI path |
| QG-INT | PARTIAL | Ownership/SSRF/malware(fake) covered; real ClamAV client missing |
| QG-E2E | PARTIAL | Playwright local; not mandatory in CI yet |
| QG-SEC | **FAIL / BLOCK** | CSRF full token needs_review; container/IaC depth; no dedicated SAST (bandit) in CI until wired |
| QG-AI | PASS (synthetic) | Gate harness enforces citation + unsupported claim threshold on golden set |
| QG-PDF | PASS (local/CI) | Pixel diff artifact path exists |
| QG-PRIV | **FAIL / BLOCK** | Legal drafts; backup deletion policy placeholder; drill evidence generated locally only |
| QG-REL | PARTIAL | Migration rollback in CI; restore drill script exists — staging restore not signed off |
| QG-A11Y | PARTIAL | axe in e2e; browser matrix not fully executed |
| QG-OPS | PASS (doc) | Runbooks + checklist published |
| QG-LEGAL | **FAIL / BLOCK** | `legal/manifest.json` status=draft; approvals pending |
| QG-CI | PASS (doc) | Clean-clone instructions published |

---

## Blockers (owner + deadline)

| ID | Blocker | Severity | Owner | Deadline |
|----|---------|----------|-------|----------|
| B-01 | Legal package draft + placeholders; no lawyer/privacy approve | critical | LegalReview + Privacy | 2026-08-25 |
| B-02 | Live RU payment credentials + contract; sandbox_only in prod forbidden | critical | Eng + Legal | 2026-09-01 |
| B-03 | Real ClamAV (or approved AV) provider wired + quarantine drill signed | high | Sec + Eng | 2026-08-28 |
| B-04 | Backup erasure / key hierarchy policy completed (`KEY_HIERARCHY_NEEDS_REVIEW`) | critical | Privacy + Ops | 2026-08-28 |
| B-05 | Staging restore drill signed evidence (not only script dry-run) | high | Eng + Ops | 2026-08-22 |
| B-06 | CSRF double-submit or equivalent reviewed beyond Origin/SameSite | high | Sec | 2026-08-22 |
| B-07 | Owner legal/tariff placeholders replaced in offer | critical | Product + Legal | 2026-08-25 |
| B-08 | Browser matrix + mobile pass recorded | medium | QA | 2026-08-29 |
| B-09 | Bandit/pip-audit hard-fail policy tuned (no silent `\|\| true` on critical) | high | Sec + Eng | 2026-08-22 |
| B-10 | Form/source manual approvals for MVP catalog | critical | LegalReview + Eng | 2026-08-25 |

---

## Synthetic staging constraints

- No real user PII; emails like `user_a@example.invalid`.
- No production payment API calls.
- No live official egress except allowlisted fetcher tests with fixtures.
- AI eval uses golden fixtures only.

---

## Sign-off

| Role | Name | Decision | Date |
|------|------|----------|------|
| Eng | TBD | NO-GO | 2026-08-11 |
| Sec | TBD | NO-GO | 2026-08-11 |
| Privacy | TBD | NO-GO | 2026-08-11 |
| LegalReview | TBD | NO-GO | 2026-08-11 |
| Product | TBD | NO-GO | 2026-08-11 |

Re-run this report after B-01…B-10 close. Only then consider GO.
