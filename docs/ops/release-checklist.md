# Release checklist

Copy to release ticket. Mark each with ✅/❌. Any ❌ on critical → **NO-GO**.

## Pre-release

- [ ] `docs/quality/quality-gates.md` reviewed; no open **critical** gates without waiver
- [ ] Traceability updated for new high-risk changes
- [ ] Legal package: lawyer + privacy_officer approved; no placeholders (`LEGAL_ROOT` gate)
- [ ] Forms published only with four-eyes; withdrawn forms not served
- [ ] Source snapshots approved; fetcher allowlist current
- [ ] `APPROVED_OFFER_VERSION` + live payment credentials if billing live
- [ ] Staging go/no-go report attached (`docs/ops/staging-go-no-go.md`)
- [ ] AI eval artifact: unsupported claim rate ≤ threshold
- [ ] Security: gitleaks, Trivy CRITICAL/HIGH clean (or accepted risk)
- [ ] Restore drill evidence present under `artifacts/drills/`
- [ ] Deletion drill evidence present under `artifacts/drills/`
- [ ] Migration upgrade/downgrade tested on staging DB
- [ ] Runbooks linked in on-call wiki
- [ ] Feature flags / degraded modes documented

## Deploy

- [ ] Clean clone CI green on release tag
- [ ] Secrets rotated / not from `.env.example`
- [ ] Fake providers forbidden (`ALLOW_FAKE_PROVIDERS=false`)
- [ ] Backup taken before migrate
- [ ] Smoke: `/health`, register, upload fixture, delete request

## Post-release

- [ ] Error budget / SLO dashboards watched 24h
- [ ] Incident channel staffed
- [ ] Rollback plan validated (app + model version pin)
