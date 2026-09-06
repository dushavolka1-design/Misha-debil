"""Real PostgreSQL migration integration: upgrade, insert, downgrade boundary, upgrade."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{API_DIR}{os.pathsep}{ROOT / 'packages' / 'py_dar' / 'src'}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.integration
def test_migration_upgrade_insert_downgrade_upgrade() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or "sqlite" in db_url.lower():
        pytest.skip("DATABASE_URL PostgreSQL required for integration migration test")

    head = _alembic("upgrade", "head")
    assert head.returncode == 0, head.stderr

    from sqlalchemy import create_engine, text

    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
    if sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(sync_url)
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO users (id, tenant_id, email, role, status, created_at, updated_at)
                VALUES (:id, :tenant, :email, 'user', 'active', now(), now())
                """
            ),
            {"id": user_id, "tenant": tenant_id, "email": f"migtest-{user_id.hex[:8]}@example.com"},
        )
        row = conn.execute(text("SELECT email FROM users WHERE id = :id"), {"id": user_id}).scalar_one()
        assert row.endswith("@example.com")

    down = _alembic("downgrade", "0008_billing")
    assert down.returncode == 0, down.stderr

    up = _alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr

    with engine.begin() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM app_state_blobs")).scalar_one()
        assert cnt is not None
