# CI from a clean clone

All commands below must succeed on a fresh checkout (no local caches required beyond package installs).

## Prerequisites

- Node 20+, pnpm 9.15.9
- Python 3.12+ (CI) / 3.14 local ok for API tests
- Docker (for migrations job / staging compose)

## JavaScript

```bash
pnpm install --frozen-lockfile
pnpm format:check
pnpm lint
pnpm typecheck
pnpm contracts:check
pnpm test:unit
```

## Python API

```bash
cd apps/api
python -m pip install -U pip
python -m pip install -e ../../packages/py_dar
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
# fonts for form-fill (Linux CI): sudo apt-get install -y fonts-dejavu-core
export APP_ENV=test ALLOW_FAKE_PROVIDERS=true
# … plus DATABASE_URL/REDIS/S3/SESSION_SECRET as in .github/workflows/ci.yml
python -m ruff check app tests ../../packages/py_dar/src
python -m mypy app
python -m pytest -q tests ../../tests/smoke/test_migrations.py ../../tests/smoke/test_health.py ../../packages/py_dar/tests
python -m app.scripts.run_ai_eval
python -m app.scripts.run_privacy_drill
python -m app.scripts.run_restore_drill
```

## Migrations (needs Postgres)

```bash
cd apps/api && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

## Security scans (as in CI)

- gitleaks
- Trivy fs CRITICAL,HIGH
- prod compose forbidden markers

## E2E (optional locally; wire to CI when browsers available)

```bash
pnpm test:e2e
```

One-shot local proxy: `pnpm ci:local` (JS subset) + API pytest as above.
