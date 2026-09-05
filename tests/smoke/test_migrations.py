from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "apps" / "api" / "alembic" / "versions" / "0001_initial.py"


def test_initial_migration_has_upgrade_and_downgrade() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "def upgrade()" in text
    assert "def downgrade()" in text
    assert "op.create_table(\n        \"users\"" in text or 'op.create_table(\n        "users"' in text
    assert "op.drop_table(\"users\")" in text or 'op.drop_table("users")' in text


def test_migration_rollback_script_documented() -> None:
    readme = (ROOT / "infra" / "README.md").read_text(encoding="utf-8")
    assert "alembic downgrade -1" in readme
    assert "alembic upgrade head" in readme
