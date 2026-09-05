# Browser / a11y / performance matrix (этап 14)

| Surface | Chrome latest | Firefox latest | Safari 17+ | Mobile 360 CSS | axe serious/critical |
|---------|---------------|----------------|------------|----------------|----------------------|
| Landing `/` | required | required | required | e2e overflow | e2e |
| Register/Login | required | smoke | smoke | e2e | TBD |
| Upload / report | required | smoke | smoke | e2e | e2e report |
| Entry wizard | required | smoke | TBD | e2e | TBD |
| Forms fill | required | TBD | TBD | e2e | TBD |
| Billing / profile | required | smoke | TBD | e2e | TBD |

Performance budgets (`PERF_BUDGET_NEEDS_REVIEW`): LCP/INP not gated in CI yet — track as medium gate QG-A11Y.

Evidence: Playwright `apps/web/e2e/ux.spec.ts`, `hardening.spec.ts`. Not yet mandatory in GitHub Actions (browser install cost) — local/QA required before GO.
