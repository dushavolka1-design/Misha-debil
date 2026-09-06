# Data inventory (privacy)

Synthetic / staging only. Placeholders: `PROCESSOR_*`, `DATA_LOCATIONS`, `RETENTION_*_NEEDS_REVIEW`.

| Data class | Store | Retention | Access | Notes |
|------------|-------|-----------|--------|-------|
| Account email | DB `users` | account lifetime + legal hold stub | user, support (meta), admin+audit | hashed password only |
| Consent events | append-only | audit retention | privacy officer, user proof | immutable published legal |
| Document originals | object storage originals bucket | `RETENTION_ORIGINALS_DAYS` | owner; break-glass+audit | separate from derived |
| Derived/OCR | derived bucket | `RETENTION_DERIVED_DAYS` | owner | never log full text |
| Reports | reports bucket | `RETENTION_REPORTS_DAYS` | owner | disclaimer required |
| Medical originals | medical retention policy | shorter medical days | medical consent gate | special category |
| Payment refs | billing provider + DB refs | per offer | user history (no PAN) | opaque tokens only |
| Webhook raw (sanitized) | billing in-memory/DB | 30 days | billing admin | strip PAN/email |
| Audit events | `audit_events` | `RETENTION_AUDIT_DAYS` | admin/privacy | tamper-evident append |
| Backups | `BACKUP_LOCATION_NEEDS_REVIEW` | must follow erasure policy | ops least-privilege | see runbook breach/restore |

## Least privilege (target)

- App role: CRUD own tenant rows; no cross-tenant.
- Support: metadata only without break-glass.
- Privacy: consent/audit; document content only with reason code.
- Backup keys: separate from app runtime keys (`KEY_HIERARCHY_NEEDS_REVIEW`).

## Processor / config check

Staging compose must not set production secrets. Prod compose scanned in CI for `change_me` / fake providers.
