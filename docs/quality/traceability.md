# Traceability: requirement → code → test → evidence

Generated for этап 14. Update when adding high-risk features.  
Gates: [quality-gates.md](quality-gates.md). Acceptance IDs: [../product/acceptance-matrix.md](../product/acceptance-matrix.md).

| Req / FR | Code | Test | Evidence |
|----------|------|------|----------|
| AT-FR-01 storage isolation | `services/upload/lifecycle.py`, buckets in settings | `test_upload_lifecycle.py` | CI unit; MinIO prefixes |
| AT-FR-02 fact provenance | `analysis/validate.py`, `schema.py` | `test_analysis_pipeline.py`, `test_ai_eval.py` | reject without citation |
| AT-FR-03 disclaimer | `@dar/ui` Disclaimer, report/billing pages | `e2e/auth-consent.spec.ts` | Playwright |
| AT-FR-04 approved sources only | `sources/registry.py`, form catalog | `test_source_registry.py`, `test_forms_medical.py` | draft → needs_review |
| AT-FR-05 IDOR | `assert_document_access`, compare ownership | `test_security_hardening.py`, `test_rules_report.py` | 403/404 |
| AT-FR-06 signed URL TTL/revoke | upload presign + delete | `test_security_hardening.py`, upload tests | expired denied |
| AT-FR-07 job idempotency | worker + analysis store | `apps/worker/tests`, billing idempotency | duplicate safe |
| AT-FR-08 consent gate | `auth_consent.py`, FEATURE_GATES | `test_auth_consent.py`, e2e | re-consent on bump |
| AT-FR-09 erasure | privacy router, retention purge | `test_privacy_drills.py` | `artifacts/drills/deletion_*` |
| AT-FR-11 underlay coords | form fill pixel_diff | `test_form_fill.py` | `artifacts/pixel-diff/` |
| AT-FR-12 no lawyer/doctor | `eval/policy.py`, LLM_SYSTEM | `test_ai_eval.py` | unsupported claim rate |
| AT-FR-13 compare | `rules/compare.py` | `test_rules_report.py` | golden compare |
| AT-NFR-03 log redaction | `upload/safe_logging.py` | `test_logging_redaction.py`, privacy canaries | canary scan |
| AT-SLO-UPLOAD | lifecycle size/page limits | `test_upload_lifecycle.py` | API errors |
| AT-UNCERT | uncertainty_state, deadlines needs_review | entry/analysis tests | no false certainty |
| AT-THR-MALWARE | FakeMalwareScanner + quarantine | upload eicar fixture | quarantine path |
| AT-THR-INJECT | eval malicious corpus | `test_ai_eval.py` | abstention |
| AT-THR-SSRF | `sources/url_policy.py` | `test_security_hardening.py` | private IP blocked |
| AT-THR-SUPPLY | lockfile + CI trivy/gitleaks | `.github/workflows/ci.yml` | security job |
| AT-THR-RECOVERY | restore drill script | `test_reliability.py`, drill script | `artifacts/drills/restore_*` |
| Billing QG | `services/billing/*`, PaymentProvider | `test_billing.py` | no double charge; forged webhook reject |
| Legal package | `dar/legal_gate.py` | `test_legal_package.py` | prod fails on draft |
| PDF form fill | `forms/fill/*` | `test_form_fill.py` | pixel/static diff |
| Entry deadlines | `entry/deadlines.py` | `test_entry_wizard.py` | needs_review calendar |
| Retention | `upload/retention.py` | upload + privacy drills | purge evidence |

## Coverage notes

- Rows without green CI evidence for restore/deletion drills → **QG-PRIV / QG-REL open** (see go/no-go blockers).
- Real ClamAV provider not wired → AT-THR-MALWARE **partial** (fake + compose service only).
- CSRF: Origin check middleware + SameSite; full double-submit token **needs_review**.
