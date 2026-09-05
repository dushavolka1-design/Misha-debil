# Redesign report — partial review increment

Date2026-09-06. Base master7ab48303efa92b2e52702256dcdd360c9540d273. Branch astra/docly-modern-redesign-20260906.

## Scope
Auth/design-foundation increment, NOT the complete requested Docly redesign. Paused technical/legal audit files are not included. No master merge, force push or deployment.

## Changes
Staged credentials/consents; existing-client auth adapters with mutation retries disabled; pending/errors; PasswordInput/Stepper; scoped light/dark CSS; no repeated password/signup avatar; source tests/Storybook examples. Existing profile/avatar and unrelated billing/disclaimer assertions retained.

## Executed evidence
- Node/tsx consent/account model:9 passed,0 failed.
- Isolated Chromium AuthFlow harness:25 responsive checks, including register/consents/login at320,375,390,768,1024,1280,1440,1920 and completion390; no horizontal overflow.
- Browser checks: password visibility, required accepts, marketing omitted, one submission on double click, failed legal load blocks submission; no page errors.
- Four selected dark text contrast pairs:14.41,8.15,9.36,8.91; NOT whole-screen AA proof.
- Local changed-source formatting executed; not repository-configured format:check.

Harness uses actual new AuthFlow/PasswordInput/Stepper with synthetic callbacks and primitive adapters, NOT full @dar/ui, MarketingShell, Next.js or FastAPI. Screenshots are browser-rendered DOM snapshots from that harness, not production screenshots or accepted visual baselines. Mobile double gutters were found visually and corrected. Scrollable legal text is intentional.

## Not completed
Sandbox clone failed DNS; Next, @playwright/test, axe and React type declarations unavailable. pnpm install and full repository format:check/lint/typecheck/contracts:check/test:unit/build/storybook/test:e2e NOT completed. No passing exit codes claimed. No Lighthouse/axe, real app bundle/LCP/CLS/INP, Windows launcher, backend/database E2E result.

## Evidence delivery
Review ZIP contains source, required design docs, QA harness, model/browser logs, results.json and inspected screenshot PNGs/manifest. Screenshots scope is registration/consents/login/completion/legal-error, not all product screens.

## Blockers
Full route audit; shell/navigation/dashboard; wizard/forms/fill/preview; upload/analysis/history; sources; privacy/security/subscription redesign; real notifications; onboarding/email/reset; localization/font audit; whole-app dark mode; WCAG/axe/Lighthouse; full compilation/contracts/E2E/visual/performance checks.

## Verdict
NOT READY for complete redesign, merge or deployment. Partial auth increment can be reviewed independently. Isolated passing QA is not a release gate.
