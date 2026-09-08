# All-branches integration evidence

main is not used as an input branch. Its current commit equals backup-before-merge; that shared history is necessarily included via the requested backup branch. Snapshots pinned on 2026-09-08.

| Branch | Snapshot | Result |
| --- | --- | --- |
| master | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| astra/docly-full-audit-20260906 | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| astra/docly-windows-installer-20260906 | 7ab48303efa92b2e52702256dcdd360c9540d273 | Already included (ancestor of HEAD) |
| backup-before-merge | d4e6da60507efb3f6aed78a1dd8ccd294e453386 | Already included (ancestor of HEAD) |
| astra/docly-modern-redesign-20260906 | db099db89d57a24a1255a545463cdd65e76c839c | Already included (ancestor of HEAD) |
| fix/docly-desktop-upgrade-safety | 59fe9e57b6bdf50083d5a261a45cb1ad4b6f092d | Merged; reviewed README conflict resolved, originals in docs/branch-history |
| chore/docly-fast-windows-installer | 04372810841cf9839f1c97afec2b7690b3fa684b | Already included (ancestor of HEAD) |

All requested snapshot commits are ancestors of the integrated HEAD.

## Net changes versus installer baseline
```text
 .github/workflows/ci.yml                           |  53 ++-
 .github/workflows/docly-checkpoint-diagnostics.yml |  63 +++
 .github/workflows/docly-ci-diagnostics.yml         |  89 ++++
 .github/workflows/docly-dependency-repair.yml      | 113 ++++++
 .github/workflows/docly-desktop-verification.yml   | 153 +++++++
 .github/workflows/docly-format.yml                 | 139 +++++++
 .github/workflows/docly-history-security.yml       |  70 ++++
 .github/workflows/docly-import-cleanup.yml         |  87 ++++
 .github/workflows/docly-installer-checksum.yml     |  38 ++
 .github/workflows/docly-launcher-safety.yml        |  88 ++++
 .../workflows/docly-official-source-snapshot.yml   | 118 ++++++
 .github/workflows/docly-profile-backup.yml         |  62 +++
 .github/workflows/docly-profile-restore.yml        | 102 +++++
 .github/workflows/docly-python-runtime.yml         | 114 ++++++
 .github/workflows/docly-quality-evidence.yml       | 119 ++++++
 .github/workflows/docly-quality-repair.yml         |  86 ++++
 .github/workflows/docly-queue-regressions.yml      |  53 +++
 .github/workflows/docly-security-regressions.yml   |  49 +++
 .../docly-source-evidence-diagnostics.yml          |  78 ++++
 .github/workflows/docly-template-registry.yml      |  62 +++
 .github/workflows/docly-test-contract-repair.yml   |  66 +++
 .github/workflows/docly-worker-regressions.yml     |  53 +++
 .github/workflows/windows-integrated.yml           | 137 +++++++
 README.md                                          | 356 ++++++----------
 apps/api/app/adapters/local_extract_ocr.py         |   4 +-
 apps/api/app/adapters/s3_storage.py                |  19 +-
 apps/api/app/db.py                                 |   2 +-
 apps/api/app/deps.py                               |   2 +-
 apps/api/app/desktop_backup.py                     |  75 ++++
 apps/api/app/desktop_boot.py                       |  42 +-
 apps/api/app/desktop_migration.py                  | 287 +++++++++++++
 apps/api/app/desktop_migration_files.py            |  90 +++++
 apps/api/app/main.py                               |  27 +-
 apps/api/app/models.py                             |  30 +-
 apps/api/app/persistence/bootstrap.py              | 144 +++----
 apps/api/app/persistence/demo_seed.py              |   6 +-
 apps/api/app/persistence/fill_runtime_repo.py      |  60 +--
 apps/api/app/persistence/form_catalog_codec.py     |  11 +-
 apps/api/app/persistence/sync_db.py                |   6 +-
 apps/api/app/profile_backup.py                     | 239 +++++++++++
 apps/api/app/py.typed                              |   0
 apps/api/app/routers/analysis.py                   |  53 ++-
 apps/api/app/routers/auth.py                       |  49 +--
 apps/api/app/routers/billing.py                    |  59 +--
 apps/api/app/routers/documents.py                  |  94 +++--
 apps/api/app/routers/entry.py                      |  26 +-
 apps/api/app/routers/form_fill.py                  |  62 +--
 apps/api/app/routers/forms.py                      |  37 +-
 apps/api/app/routers/health.py                     |  13 +-
 apps/api/app/routers/legal.py                      |   6 +-
 apps/api/app/routers/privacy.py                    |  17 +-
 apps/api/app/routers/reports.py                    |  61 +--
 apps/api/app/routers/sources.py                    |  29 +-
 apps/api/app/schemas.py                            |   2 +-
 apps/api/app/schemas_auth.py                       |   4 +-
 apps/api/app/schemas_billing.py                    |   1 -
 apps/api/app/schemas_documents.py                  |   5 +-
 apps/api/app/scripts/run_ai_eval.py                |   4 +-
 apps/api/app/scripts/run_privacy_drill.py          |  10 +-
 apps/api/app/scripts/run_restore_drill.py          |   8 +-
 apps/api/app/security/circuit_breaker.py           |   4 +-
 apps/api/app/security/csrf.py                      |  21 +-
 apps/api/app/services/analysis/layout.py           |   2 +-
 apps/api/app/services/analysis/metrics.py          |   4 +-
 apps/api/app/services/analysis/normalize_pages.py  |   8 +-
 apps/api/app/services/analysis/normalizers.py      |   2 +-
 apps/api/app/services/analysis/pipeline.py         |  32 +-
 apps/api/app/services/analysis/schema.py           |  22 +-
 apps/api/app/services/analysis/validate.py         |  28 +-
 apps/api/app/services/auth_consent.py              |  11 +-
 apps/api/app/services/auth_profile.py              |   4 +-
 apps/api/app/services/billing/service.py           |  32 +-
 apps/api/app/services/entry/deadlines.py           |  19 +-
 apps/api/app/services/entry/engine.py              |  19 +-
 apps/api/app/services/entry/pack.py                |  36 +-
 apps/api/app/services/eval/policy.py               |   9 +-
 apps/api/app/services/eval/runner.py               |   9 +-
 apps/api/app/services/forms/catalog.py             |   8 +-
 apps/api/app/services/forms/catalog_seed.py        |  25 +-
 apps/api/app/services/forms/fill/answer_checks.py  |   4 +-
 apps/api/app/services/forms/fill/coord_map.py      |   4 +-
 apps/api/app/services/forms/fill/engine.py         |   4 +-
 apps/api/app/services/forms/fill/fonts.py          |  39 +-
 .../app/services/forms/fill/generation_gates.py    |  34 +-
 apps/api/app/services/forms/fill/pixel_diff.py     |  27 +-
 apps/api/app/services/forms/fill/pixel_metrics.py  |  22 +
 apps/api/app/services/forms/fill/service.py        |  31 +-
 apps/api/app/services/forms/fill/underlay.py       |   4 +-
 apps/api/app/services/forms/fill/validate.py       |  10 +-
 apps/api/app/services/forms/fill/worksheets.py     |  34 +-
 apps/api/app/services/forms/medical.py             |  17 +-
 apps/api/app/services/forms/official_form_acts.py  |   6 +-
 apps/api/app/services/forms/official_intake.py     |   8 +-
 apps/api/app/services/forms/pdf_memo.py            |  17 +-
 apps/api/app/services/jobs/broker.py               |  38 +-
 apps/api/app/services/jobs/consumer.py             |   5 +-
 apps/api/app/services/jobs/runner.py               |   3 +-
 apps/api/app/services/jobs/worker_runtime.py       |  12 +-
 apps/api/app/services/legal_package.py             |   4 +-
 apps/api/app/services/rules/compare.py             |   9 +-
 apps/api/app/services/rules/engine.py              |  23 +-
 apps/api/app/services/rules/feedback.py            |   8 +-
 apps/api/app/services/rules/registry.py            | 206 ++++++++--
 apps/api/app/services/rules/report.py              |  18 +-
 apps/api/app/services/sources/fetcher.py           |   4 +-
 apps/api/app/services/sources/registry.py          |  43 +-
 apps/api/app/services/sources/url_policy.py        |   4 +-
 apps/api/app/services/upload/filename.py           |  18 +-
 apps/api/app/services/upload/fsm.py                |   8 +-
 apps/api/app/services/upload/lifecycle.py          |  17 +-
 apps/api/app/services/upload/retention.py          |  11 +-
 apps/api/app/services/upload/safe_logging.py       |  31 +-
 apps/api/pyproject.toml                            |   3 +
 apps/api/tests/conftest.py                         |  60 ++-
 apps/api/tests/docly_auth_test_support.py          |  26 ++
 apps/api/tests/test_ai_eval.py                     |   2 -
 apps/api/tests/test_analysis_pipeline.py           |   1 -
 apps/api/tests/test_analysis_schema_boundaries.py  |  87 ++++
 apps/api/tests/test_answer_checks.py               |   2 +-
 apps/api/tests/test_auth_consent.py                |  32 +-
 apps/api/tests/test_auth_route_regressions.py      | 138 +++++++
 apps/api/tests/test_billing.py                     |  14 +-
 apps/api/tests/test_csrf_referer_origin.py         |  68 ++++
 apps/api/tests/test_desktop_backup.py              | 120 ++++++
 apps/api/tests/test_desktop_backup_flush.py        |  45 +++
 apps/api/tests/test_desktop_launcher_e2e.py        |  22 +-
 apps/api/tests/test_desktop_profile.py             |  12 +-
 apps/api/tests/test_desktop_profile_backup.py      | 186 +++++++++
 apps/api/tests/test_document_log_arguments.py      |  47 +++
 .../test_document_maintenance_authorization.py     |  88 ++++
 apps/api/tests/test_entry_wizard.py                |  34 +-
 apps/api/tests/test_filename_controls.py           |  26 ++
 apps/api/tests/test_font_manifest_safety.py        | 105 +++++
 apps/api/tests/test_form_catalog_api_contract.py   |  11 +-
 apps/api/tests/test_form_catalog_persistence.py    |   1 -
 apps/api/tests/test_form_fill.py                   |   1 -
 apps/api/tests/test_forms_medical.py               |  16 +-
 apps/api/tests/test_generation_gate_contract.py    |  21 +
 apps/api/tests/test_job_broker_claim.py            |  84 ++++
 apps/api/tests/test_legal_package.py               |   2 -
 apps/api/tests/test_local_extract_contract.py      |  41 ++
 apps/api/tests/test_local_facts_excerpt.py         |   8 +-
 apps/api/tests/test_logging_redaction.py           |   1 +
 apps/api/tests/test_pixel_metrics.py               |  53 +++
 apps/api/tests/test_prompt3_generation_guards.py   |   8 +-
 apps/api/tests/test_prompt5_scenarios.py           |   6 +-
 apps/api/tests/test_prompt6_acceptance.py          |  21 +-
 apps/api/tests/test_prompt8_gate.py                |  52 ++-
 apps/api/tests/test_reliability.py                 |   3 +-
 apps/api/tests/test_rules_report.py                |  51 ++-
 apps/api/tests/test_s3_storage_boundaries.py       |  71 ++++
 apps/api/tests/test_security_hardening.py          |  10 +-
 apps/api/tests/test_source_registry.py             |   5 +-
 apps/api/tests/test_upload_lifecycle.py            |  26 +-
 apps/api/tests/test_worksheets_official_acts.py    |  13 +-
 apps/web/e2e/auth-consent.spec.ts                  |  21 +-
 apps/web/e2e/helpers.ts                            |   4 +-
 apps/web/e2e/prompt6-acceptance.spec.ts            |  12 +-
 apps/web/e2e/prompt8-final.spec.ts                 |  53 ++-
 apps/web/e2e/ux.spec.ts                            |   9 +-
 apps/web/eslint.config.mjs                         |  21 +-
 apps/web/next.config.ts                            |  12 +-
 apps/web/package.json                              |   2 +-
 apps/web/playwright.config.ts                      |  14 +-
 apps/web/public/docly-runtime.js                   |   2 +-
 .../web/src/app/app/analyzer/AnalyzerHubClient.tsx |   6 +-
 .../src/app/app/analyzer/ComparePanelClient.tsx    |  50 ++-
 .../src/app/app/analyzer/DocumentDetailView.tsx    |  57 ++-
 .../src/app/app/analyzer/DocumentsPanelClient.tsx  |  66 ++-
 apps/web/src/app/app/billing/BillingClient.tsx     |  48 ++-
 apps/web/src/app/app/compare/page.tsx              |   8 +-
 .../src/app/app/entry-wizard/EntryWizardClient.tsx | 139 +++++--
 apps/web/src/app/app/forms/FormsCatalogClient.tsx  |  95 +++--
 apps/web/src/app/app/forms/[id]/FormFillClient.tsx |  97 ++++-
 .../app/app/generator/CreatedDocumentsPanel.tsx    |  25 +-
 .../src/app/app/generator/GeneratorHubClient.tsx   |   3 +-
 .../src/app/app/jobs/[id]/JobProgressClient.tsx    |   9 +-
 apps/web/src/app/app/page.tsx                      |   4 +-
 apps/web/src/app/app/profile/ProfileClient.tsx     |  61 ++-
 apps/web/src/app/app/sources/page.tsx              |  23 +-
 apps/web/src/app/app/upload/UploadClient.tsx       | 117 +++---
 apps/web/src/app/auth/login/LoginClient.tsx        |  98 +----
 apps/web/src/app/auth/register/page.tsx            | 334 +--------------
 apps/web/src/app/layout.tsx                        |   2 +-
 apps/web/src/app/page.tsx                          |  38 +-
 apps/web/src/components/AnalysisProgressCard.tsx   |  30 +-
 apps/web/src/components/DeleteDocumentDialog.tsx   |   4 +-
 apps/web/src/components/DemoModeBanner.tsx         |   7 +-
 apps/web/src/components/ReportWorkspace.tsx        |  10 +-
 apps/web/src/components/SectionErrorBoundary.tsx   |   4 +-
 apps/web/src/components/Shell.tsx                  | 134 +++---
 apps/web/src/components/auth/AuthClient.tsx        |  59 +++
 apps/web/src/components/auth/AuthFlow.tsx          | 449 +++++++++++++++++++++
 apps/web/src/components/auth/authModel.test.ts     |  74 ++++
 apps/web/src/components/auth/authModel.ts          |  70 ++++
 apps/web/src/eslint-config.test.mjs                |  59 +++
 apps/web/src/lib/answerChecks.test.ts              |   4 +-
 apps/web/src/lib/answerChecks.ts                   |   3 +-
 apps/web/src/lib/apiBase.ts                        |   8 +-
 apps/web/src/lib/apiClient.ts                      | 222 ++++------
 apps/web/src/register.profile.test.ts              |  22 +-
 apps/web/src/styles/app.css                        |  46 ++-
 apps/web/test-results/.last-run.json               |   2 +-
 apps/worker/tests/test_worker_shutdown.py          | 130 ++++++
 apps/worker/worker/main.py                         |  60 ++-
 docly                                              |   1 +
 docs/branch-history/backup-before-merge.README.md  |   2 +
 docs/branch-history/desktop-safety.README.md       | 154 +++++++
 docs/branch-history/pre-integration.README.md      | 298 ++++++++++++++
 docs/design/design-system.md                       |  21 +
 docs/design/information-architecture.md            |  22 +
 docs/design/redesign-audit.md                      |  29 ++
 docs/design/redesign-report.md                     |  30 ++
 docs/design/registration-flow.md                   |  18 +
 docs/integration/legacy-main-README.md             |   2 +
 docs/ops/profile-backup.md                         |  19 +
 docs/verification/mvd-290-2026-source-review.md    |  59 +++
 installer/INTEGRATED-CI.md                         |  12 +
 installer/INTEGRATED-STATUS.md                     |  11 +
 installer/INTEGRATION.md                           |  24 ++
 installer/integrate-branches.py                    | 112 +++++
 package.json                                       |   6 +
 packages/contracts/package.json                    |   2 +-
 packages/py_dar/src/dar/legal_gate.py              |   5 +-
 packages/py_dar/src/dar/providers/fake.py          |   2 +-
 packages/py_dar/src/dar/providers/ports.py         |   6 +-
 .../py_dar/src/dar/providers/ru_payment_sandbox.py |  14 +-
 .../py_dar/src/dar/providers/ru_private_llm.py     |   2 +-
 .../py_dar/src/dar/providers/ru_private_ocr.py     |   2 +-
 .../py_dar/src/dar/providers/unavailable_llm.py    |   2 +-
 packages/py_dar/src/dar/py.typed                   |   0
 packages/py_dar/src/dar/settings_base.py           |   7 +-
 packages/ui/package.json                           |   2 +-
 packages/ui/src/Feedback.tsx                       |  15 +-
 packages/ui/src/Icon.tsx                           |   7 +-
 packages/ui/src/PasswordInput.tsx                  |  92 +++++
 packages/ui/src/ScreenState.tsx                    |   8 +-
 packages/ui/src/Stepper.tsx                        |  20 +
 packages/ui/src/TemplateCard.tsx                   |   7 +-
 packages/ui/src/fonts/onest/onest.css              |  12 +-
 packages/ui/src/index.ts                           |  12 +-
 packages/ui/src/prompt4.tokens.test.ts             |  13 +-
 packages/ui/src/stories/AuthControls.stories.tsx   |  38 ++
 packages/ui/src/stories/Typography.stories.tsx     |   4 +-
 packages/ui/src/styles/auth-foundation.css         | 367 +++++++++++++++++
 packages/ui/src/styles/components.css              |   7 +-
 packages/ui/src/styles/index.css                   |   1 +
 pnpm-lock.yaml                                     | 295 +++++++-------
 scripts/audit_template_inventory.py                |  75 ++++
 scripts/build_template_review_registry.py          | 163 ++++++++
 scripts/repair_desktop_auth_test_contracts.py      |  58 +++
 scripts/repair_runtime_fixture_alignment.py        |  69 ++++
 scripts/reviewed_import_cleanup.py                 |  92 +++++
 scripts/reviewed_quality_fixes.py                  | 141 +++++++
 scripts/run-node-tests.mjs                         |  37 ++
 scripts/test_template_review_registry.py           |  96 +++++
 scripts/verify_history_scan.py                     |  93 +++++
 scripts/windows/build-installer.ps1                |  58 +++
 scripts/windows/docly.iss                          |  89 ++++
 scripts/windows/docly_launcher.py                  | 440 ++++++++++++--------
 scripts/windows/install-runtime.ps1                |  15 +
 scripts/windows/install-shortcuts.vbs              | 109 ++---
 scripts/windows/launch-installed.vbs               |  17 +
 scripts/windows/profile_restore.py                 |  88 ++++
 scripts/windows/setup-desktop.ps1                  | 132 +++---
 scripts/windows/stage-runtime.py                   |  75 ++++
 scripts/windows/test-installer-checksum.ps1        |  52 +++
 scripts/windows/test-installer.ps1                 | 160 ++++++++
 scripts/windows/test_launcher_safety.py            | 169 ++++++++
 scripts/windows/test_launcher_windows.py           |  52 +++
 scripts/windows/test_profile_restore.py            | 219 ++++++++++
 sources/allowlist.json                             |   8 +-
 tests/fixtures/analysis/expected.json              |  12 +-
 273 files changed, 11083 insertions(+), 2598 deletions(-)

```

## Changed paths
```text
M	.github/workflows/ci.yml
A	.github/workflows/docly-checkpoint-diagnostics.yml
A	.github/workflows/docly-ci-diagnostics.yml
A	.github/workflows/docly-dependency-repair.yml
A	.github/workflows/docly-desktop-verification.yml
A	.github/workflows/docly-format.yml
A	.github/workflows/docly-history-security.yml
A	.github/workflows/docly-import-cleanup.yml
A	.github/workflows/docly-installer-checksum.yml
A	.github/workflows/docly-launcher-safety.yml
A	.github/workflows/docly-official-source-snapshot.yml
A	.github/workflows/docly-profile-backup.yml
A	.github/workflows/docly-profile-restore.yml
A	.github/workflows/docly-python-runtime.yml
A	.github/workflows/docly-quality-evidence.yml
A	.github/workflows/docly-quality-repair.yml
A	.github/workflows/docly-queue-regressions.yml
A	.github/workflows/docly-security-regressions.yml
A	.github/workflows/docly-source-evidence-diagnostics.yml
A	.github/workflows/docly-template-registry.yml
A	.github/workflows/docly-test-contract-repair.yml
A	.github/workflows/docly-worker-regressions.yml
A	.github/workflows/windows-integrated.yml
M	README.md
M	apps/api/app/adapters/local_extract_ocr.py
M	apps/api/app/adapters/s3_storage.py
M	apps/api/app/db.py
M	apps/api/app/deps.py
A	apps/api/app/desktop_backup.py
M	apps/api/app/desktop_boot.py
A	apps/api/app/desktop_migration.py
A	apps/api/app/desktop_migration_files.py
M	apps/api/app/main.py
M	apps/api/app/models.py
M	apps/api/app/persistence/bootstrap.py
M	apps/api/app/persistence/demo_seed.py
M	apps/api/app/persistence/fill_runtime_repo.py
M	apps/api/app/persistence/form_catalog_codec.py
M	apps/api/app/persistence/sync_db.py
A	apps/api/app/profile_backup.py
A	apps/api/app/py.typed
M	apps/api/app/routers/analysis.py
M	apps/api/app/routers/auth.py
M	apps/api/app/routers/billing.py
M	apps/api/app/routers/documents.py
M	apps/api/app/routers/entry.py
M	apps/api/app/routers/form_fill.py
M	apps/api/app/routers/forms.py
M	apps/api/app/routers/health.py
M	apps/api/app/routers/legal.py
M	apps/api/app/routers/privacy.py
M	apps/api/app/routers/reports.py
M	apps/api/app/routers/sources.py
M	apps/api/app/schemas.py
M	apps/api/app/schemas_auth.py
M	apps/api/app/schemas_billing.py
M	apps/api/app/schemas_documents.py
M	apps/api/app/scripts/run_ai_eval.py
M	apps/api/app/scripts/run_privacy_drill.py
M	apps/api/app/scripts/run_restore_drill.py
M	apps/api/app/security/circuit_breaker.py
M	apps/api/app/security/csrf.py
M	apps/api/app/services/analysis/layout.py
M	apps/api/app/services/analysis/metrics.py
M	apps/api/app/services/analysis/normalize_pages.py
M	apps/api/app/services/analysis/normalizers.py
M	apps/api/app/services/analysis/pipeline.py
M	apps/api/app/services/analysis/schema.py
M	apps/api/app/services/analysis/validate.py
M	apps/api/app/services/auth_consent.py
M	apps/api/app/services/auth_profile.py
M	apps/api/app/services/billing/service.py
M	apps/api/app/services/entry/deadlines.py
M	apps/api/app/services/entry/engine.py
M	apps/api/app/services/entry/pack.py
M	apps/api/app/services/eval/policy.py
M	apps/api/app/services/eval/runner.py
M	apps/api/app/services/forms/catalog.py
M	apps/api/app/services/forms/catalog_seed.py
M	apps/api/app/services/forms/fill/answer_checks.py
M	apps/api/app/services/forms/fill/coord_map.py
M	apps/api/app/services/forms/fill/engine.py
M	apps/api/app/services/forms/fill/fonts.py
M	apps/api/app/services/forms/fill/generation_gates.py
M	apps/api/app/services/forms/fill/pixel_diff.py
A	apps/api/app/services/forms/fill/pixel_metrics.py
M	apps/api/app/services/forms/fill/service.py
M	apps/api/app/services/forms/fill/underlay.py
M	apps/api/app/services/forms/fill/validate.py
M	apps/api/app/services/forms/fill/worksheets.py
M	apps/api/app/services/forms/medical.py
M	apps/api/app/services/forms/official_form_acts.py
M	apps/api/app/services/forms/official_intake.py
M	apps/api/app/services/forms/pdf_memo.py
M	apps/api/app/services/jobs/broker.py
M	apps/api/app/services/jobs/consumer.py
M	apps/api/app/services/jobs/runner.py
M	apps/api/app/services/jobs/worker_runtime.py
M	apps/api/app/services/legal_package.py
M	apps/api/app/services/rules/compare.py
M	apps/api/app/services/rules/engine.py
M	apps/api/app/services/rules/feedback.py
M	apps/api/app/services/rules/registry.py
M	apps/api/app/services/rules/report.py
M	apps/api/app/services/sources/fetcher.py
M	apps/api/app/services/sources/registry.py
M	apps/api/app/services/sources/url_policy.py
M	apps/api/app/services/upload/filename.py
M	apps/api/app/services/upload/fsm.py
M	apps/api/app/services/upload/lifecycle.py
M	apps/api/app/services/upload/retention.py
M	apps/api/app/services/upload/safe_logging.py
M	apps/api/pyproject.toml
M	apps/api/tests/conftest.py
A	apps/api/tests/docly_auth_test_support.py
M	apps/api/tests/test_ai_eval.py
M	apps/api/tests/test_analysis_pipeline.py
A	apps/api/tests/test_analysis_schema_boundaries.py
M	apps/api/tests/test_answer_checks.py
M	apps/api/tests/test_auth_consent.py
A	apps/api/tests/test_auth_route_regressions.py
M	apps/api/tests/test_billing.py
A	apps/api/tests/test_csrf_referer_origin.py
A	apps/api/tests/test_desktop_backup.py
A	apps/api/tests/test_desktop_backup_flush.py
M	apps/api/tests/test_desktop_launcher_e2e.py
M	apps/api/tests/test_desktop_profile.py
A	apps/api/tests/test_desktop_profile_backup.py
A	apps/api/tests/test_document_log_arguments.py
A	apps/api/tests/test_document_maintenance_authorization.py
M	apps/api/tests/test_entry_wizard.py
A	apps/api/tests/test_filename_controls.py
A	apps/api/tests/test_font_manifest_safety.py
M	apps/api/tests/test_form_catalog_api_contract.py
M	apps/api/tests/test_form_catalog_persistence.py
M	apps/api/tests/test_form_fill.py
M	apps/api/tests/test_forms_medical.py
A	apps/api/tests/test_generation_gate_contract.py
A	apps/api/tests/test_job_broker_claim.py
M	apps/api/tests/test_legal_package.py
A	apps/api/tests/test_local_extract_contract.py
M	apps/api/tests/test_local_facts_excerpt.py
M	apps/api/tests/test_logging_redaction.py
A	apps/api/tests/test_pixel_metrics.py
M	apps/api/tests/test_prompt3_generation_guards.py
M	apps/api/tests/test_prompt5_scenarios.py
M	apps/api/tests/test_prompt6_acceptance.py
M	apps/api/tests/test_prompt8_gate.py
M	apps/api/tests/test_reliability.py
M	apps/api/tests/test_rules_report.py
A	apps/api/tests/test_s3_storage_boundaries.py
M	apps/api/tests/test_security_hardening.py
M	apps/api/tests/test_source_registry.py
M	apps/api/tests/test_upload_lifecycle.py
M	apps/api/tests/test_worksheets_official_acts.py
M	apps/web/e2e/auth-consent.spec.ts
M	apps/web/e2e/helpers.ts
M	apps/web/e2e/prompt6-acceptance.spec.ts
M	apps/web/e2e/prompt8-final.spec.ts
M	apps/web/e2e/ux.spec.ts
M	apps/web/eslint.config.mjs
M	apps/web/next.config.ts
M	apps/web/package.json
M	apps/web/playwright.config.ts
M	apps/web/public/docly-runtime.js
M	apps/web/src/app/app/analyzer/AnalyzerHubClient.tsx
M	apps/web/src/app/app/analyzer/ComparePanelClient.tsx
M	apps/web/src/app/app/analyzer/DocumentDetailView.tsx
M	apps/web/src/app/app/analyzer/DocumentsPanelClient.tsx
M	apps/web/src/app/app/billing/BillingClient.tsx
M	apps/web/src/app/app/compare/page.tsx
M	apps/web/src/app/app/entry-wizard/EntryWizardClient.tsx
M	apps/web/src/app/app/forms/FormsCatalogClient.tsx
M	apps/web/src/app/app/forms/[id]/FormFillClient.tsx
M	apps/web/src/app/app/generator/CreatedDocumentsPanel.tsx
M	apps/web/src/app/app/generator/GeneratorHubClient.tsx
M	apps/web/src/app/app/jobs/[id]/JobProgressClient.tsx
M	apps/web/src/app/app/page.tsx
M	apps/web/src/app/app/profile/ProfileClient.tsx
M	apps/web/src/app/app/sources/page.tsx
M	apps/web/src/app/app/upload/UploadClient.tsx
M	apps/web/src/app/auth/login/LoginClient.tsx
M	apps/web/src/app/auth/register/page.tsx
M	apps/web/src/app/layout.tsx
M	apps/web/src/app/page.tsx
M	apps/web/src/components/AnalysisProgressCard.tsx
M	apps/web/src/components/DeleteDocumentDialog.tsx
M	apps/web/src/components/DemoModeBanner.tsx
M	apps/web/src/components/ReportWorkspace.tsx
M	apps/web/src/components/SectionErrorBoundary.tsx
M	apps/web/src/components/Shell.tsx
A	apps/web/src/components/auth/AuthClient.tsx
A	apps/web/src/components/auth/AuthFlow.tsx
A	apps/web/src/components/auth/authModel.test.ts
A	apps/web/src/components/auth/authModel.ts
A	apps/web/src/eslint-config.test.mjs
M	apps/web/src/lib/answerChecks.test.ts
M	apps/web/src/lib/answerChecks.ts
M	apps/web/src/lib/apiBase.ts
M	apps/web/src/lib/apiClient.ts
M	apps/web/src/register.profile.test.ts
M	apps/web/src/styles/app.css
M	apps/web/test-results/.last-run.json
A	apps/worker/tests/test_worker_shutdown.py
M	apps/worker/worker/main.py
A	docly
A	docs/branch-history/backup-before-merge.README.md
A	docs/branch-history/desktop-safety.README.md
A	docs/branch-history/pre-integration.README.md
A	docs/design/design-system.md
A	docs/design/information-architecture.md
A	docs/design/redesign-audit.md
A	docs/design/redesign-report.md
A	docs/design/registration-flow.md
A	docs/integration/legacy-main-README.md
A	docs/ops/profile-backup.md
A	docs/verification/mvd-290-2026-source-review.md
A	installer/INTEGRATED-CI.md
A	installer/INTEGRATED-STATUS.md
A	installer/INTEGRATION.md
A	installer/integrate-branches.py
M	package.json
M	packages/contracts/package.json
M	packages/py_dar/src/dar/legal_gate.py
M	packages/py_dar/src/dar/providers/fake.py
M	packages/py_dar/src/dar/providers/ports.py
M	packages/py_dar/src/dar/providers/ru_payment_sandbox.py
M	packages/py_dar/src/dar/providers/ru_private_llm.py
M	packages/py_dar/src/dar/providers/ru_private_ocr.py
M	packages/py_dar/src/dar/providers/unavailable_llm.py
A	packages/py_dar/src/dar/py.typed
M	packages/py_dar/src/dar/settings_base.py
M	packages/ui/package.json
M	packages/ui/src/Feedback.tsx
M	packages/ui/src/Icon.tsx
A	packages/ui/src/PasswordInput.tsx
M	packages/ui/src/ScreenState.tsx
A	packages/ui/src/Stepper.tsx
M	packages/ui/src/TemplateCard.tsx
M	packages/ui/src/fonts/onest/onest.css
M	packages/ui/src/index.ts
M	packages/ui/src/prompt4.tokens.test.ts
A	packages/ui/src/stories/AuthControls.stories.tsx
M	packages/ui/src/stories/Typography.stories.tsx
A	packages/ui/src/styles/auth-foundation.css
M	packages/ui/src/styles/components.css
M	packages/ui/src/styles/index.css
M	pnpm-lock.yaml
A	scripts/audit_template_inventory.py
A	scripts/build_template_review_registry.py
A	scripts/repair_desktop_auth_test_contracts.py
A	scripts/repair_runtime_fixture_alignment.py
A	scripts/reviewed_import_cleanup.py
A	scripts/reviewed_quality_fixes.py
A	scripts/run-node-tests.mjs
A	scripts/test_template_review_registry.py
A	scripts/verify_history_scan.py
A	scripts/windows/build-installer.ps1
A	scripts/windows/docly.iss
M	scripts/windows/docly_launcher.py
A	scripts/windows/install-runtime.ps1
M	scripts/windows/install-shortcuts.vbs
A	scripts/windows/launch-installed.vbs
A	scripts/windows/profile_restore.py
M	scripts/windows/setup-desktop.ps1
A	scripts/windows/stage-runtime.py
A	scripts/windows/test-installer-checksum.ps1
A	scripts/windows/test-installer.ps1
A	scripts/windows/test_launcher_safety.py
A	scripts/windows/test_launcher_windows.py
A	scripts/windows/test_profile_restore.py
M	sources/allowlist.json
M	tests/fixtures/analysis/expected.json

```
