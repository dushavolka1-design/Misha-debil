# Runbook: Incident response

## Severity

- **SEV1** — data breach, auth bypass, payment double-charge, mass outage
- **SEV2** — partial degradation, elevated error rate, single-tenant impact
- **SEV3** — cosmetic / low user impact

## Steps

1. Declare severity in on-call channel; assign Incident Commander.
2. Stabilize: feature flag off, degrade to read-only, block uploads if needed.
3. Preserve evidence: logs (redacted), audit_events, deploy version, model/prompt versions.
4. User comms: factual status page; no legal conclusions in public text.
5. Fix forward or rollback (see model-rollback / release checklist).
6. Postmortem within 5 business days; link quality-gates updates.

## Contacts

`ONCALL_PRIMARY`, `SECURITY_CONTACT`, `PRIVACY_OFFICER`, `SUPPORT_EMAIL` — placeholders until staffed.
