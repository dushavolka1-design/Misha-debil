# Synthetic staging seed

Use only fictional identities. Never copy production dumps.

| Entity | Value |
|--------|-------|
| User A | `user_a@example.invalid` / password from staging vault |
| User B | `user_b@example.invalid` (for IDOR tests) |
| Admin | `admin@example.invalid` role=admin |
| Documents | `tests/fixtures/upload/clean.pdf` only |
| Consents | accept active versions from `legal/` drafts in staging only |
| Billing | `PAYMENT_PROVIDER=fake_payment` or `ru_payment_sandbox` |
| Sources | fixture snapshots; no live egress required for smoke |

After seed, run:

```bash
cd apps/api
python -m app.scripts.run_ai_eval
python -m app.scripts.run_privacy_drill
python -m app.scripts.run_restore_drill
```

Attach artifacts under `artifacts/` to go/no-go ticket.
