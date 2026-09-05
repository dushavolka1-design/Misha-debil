"""Runtime JSON columns and app_state_blobs for durable local stores."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_persistence_runtime"
down_revision = "0008_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "runtime_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "analysis_runs",
        sa.Column(
            "runtime_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_table(
        "app_state_blobs",
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("blob_key", sa.String(length=128), nullable=False),
        sa.Column(
            "value_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("namespace", "blob_key", name="pk_app_state_blobs"),
    )


def downgrade() -> None:
    op.drop_table("app_state_blobs")
    op.drop_column("analysis_runs", "runtime_json")
    op.drop_column("documents", "runtime_json")
