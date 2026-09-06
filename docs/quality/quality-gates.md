# Quality gates (этап 14)

**Статус релиза:** `NO-GO` пока любой **critical** gate открыт.  
Этот документ — источник истины для go/no-go. Не объявлять production-ready при незакрытом critical gate.

Связано: [traceability.md](traceability.md), [../ops/staging-go-no-go.md](../ops/staging-go-no-go.md), [../product/acceptance-matrix.md](../product/acceptance-matrix.md).

---

## Severity

| Level | Правило |
|-------|---------|
| **critical** | Блокирует релиз. Нет waivers без письменного Sec/Privacy/Legal owner + deadline ≤ 14 дней. |
| **high** | Блокирует релиз, если нет accepted risk с compensating control и expiry. |
| **medium** | Требует ticket + owner; не блокирует только при явном Product accept. |
| **low** | Backlog. |

---

## Gate catalog

| Gate ID | Area | Severity | Pass criterion | Evidence |
|---------|------|----------|----------------|----------|
| QG-TRACE | Traceability | high | Каждое AT-* / FR high-risk → code → test → artifact | `docs/quality/traceability.md` |
| QG-UNIT | Unit | high | Normalizers, validators, rules, deadlines, consent, form fields, retention green | `pytest apps/api/tests` |
| QG-INT | Integration | high | Ownership/IDOR, storage isolation, queue idempotency, malware policy, provider contracts, snapshots, deletion | tests + CI migrations |
| QG-E2E | E2E | high | Register/accept, upload/analysis/citation, compare, entry, form fill, billing cancel, consent withdraw, delete | Playwright + API flows |
| QG-SEC | Security | **critical** | No open CRITICAL/HIGH (Trivy/gitleaks/SAST) or release blocked; IDOR/SSRF/injection/rate-limit covered | CI security job + `test_security_hardening.py` |
| QG-AI | AI eval | **critical** | Unsupported legal claim rate ≤ threshold; findings without citation not shown; injection abstains | `pytest …/test_ai_eval.py` + `artifacts/ai-eval/` |
| QG-PDF | PDF fill | high | Masked pixel/text/static diff, geometry, font license, print smoke | `test_form_fill.py` + pixel artifact |
| QG-PRIV | Privacy | **critical** | Data inventory, log canaries, retention purge, export/delete, backup deletion policy documented; drills have evidence | `test_privacy_drills.py` + inventory |
| QG-REL | Reliability | high | Backpressure/timeout/CB, restore drill evidence, degraded modes, provider outage, migration rollback | drills + `test_reliability.py` |
| QG-A11Y | A11y/perf | medium | axe on key screens; browser matrix documented | e2e + matrix in go/no-go |
| QG-OPS | Ops | **critical** | Release checklist + runbooks published; staging synthetic; blockers listed with owner/deadline | `docs/ops/*` |
| QG-LEGAL | Legal/sources/forms | **critical** | Manual approval for forms, legal texts, sources; draft legal package blocks production | `legal/manifest.json` + registry |
| QG-CI | Clean clone | high | All CI commands repeatable from clean clone | `scripts/ci-from-clean-clone.md` |

---

## Hard block rules (readiness)

1. Critical/high security issues open → **release blocked**.
2. Unsupported legal claim rate > `UNSUPPORTED_CLAIM_RATE_MAX` (default **0.00** on synthetic gate set; staging may use 0.02 with LegalReview) → **release blocked**.
3. Any user-visible finding without valid citation → **must not be shown** (schema reject).
4. Restore and deletion drills without evidence files → **release blocked**.
5. Forms / legal texts / sources without manual approval → **release blocked**.
6. CI not reproducible from clean clone → **release blocked**.

---

## How to evaluate

```bash
# From repo root (see scripts/ci-from-clean-clone.md)
pnpm ci:local
cd apps/api && python -m pytest -q tests
python -m pytest -q tests/test_ai_eval.py --tb=short
# Evidence writers:
python -m app.scripts.run_ai_eval
python -m app.scripts.run_privacy_drill
python -m app.scripts.run_restore_drill
```

Go/no-go report: [../ops/staging-go-no-go.md](../ops/staging-go-no-go.md).
