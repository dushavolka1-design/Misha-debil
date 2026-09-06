# Local infrastructure

## Start dependencies

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d postgres redis minio minio-init clamav
```

## Migrate

```bash
cd apps/api
python -m pip install -e ../../packages/py_dar -e ".[dev]"
alembic upgrade head
```

## Rollback check (required for stage 2)

```bash
cd apps/api
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Apps profile

```bash
docker compose -f infra/docker-compose.yml --profile apps up --build api worker
```

## Production profile guard

`infra/docker-compose.prod.yml` requires non-fake providers and real secrets.
It must not be started with `ALLOW_FAKE_PROVIDERS=true`, SQLite, or `change_me` defaults.
