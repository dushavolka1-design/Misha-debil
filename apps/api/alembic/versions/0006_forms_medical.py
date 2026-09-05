"""Forms catalog metadata enrichment.

Revision ID: 0006_forms_medical
Revises: 0005_source_registry
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_forms_medical"
down_revision: Union[str, None] = "0005_source_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("form_templates", sa.Column("organ", sa.String(length=256), nullable=True))
    op.add_column("form_templates", sa.Column("purpose", sa.String(length=128), nullable=True))
    op.add_column("form_templates", sa.Column("region", sa.String(length=32), nullable=True))
    op.add_column("form_templates", sa.Column("authority", sa.String(length=256), nullable=True))

    op.add_column("form_versions", sa.Column("source_snapshot_id", sa.UUID(), nullable=True))
    op.add_column("form_versions", sa.Column("content_sha256", sa.String(length=64), nullable=True))
    op.add_column("form_versions", sa.Column("act_number", sa.String(length=128), nullable=True))
    op.add_column("form_versions", sa.Column("act_date", sa.Date(), nullable=True))
    op.add_column("form_versions", sa.Column("act_title", sa.String(length=512), nullable=True))
    op.add_column("form_versions", sa.Column("valid_from", sa.Date(), nullable=True))
    op.add_column("form_versions", sa.Column("valid_to", sa.Date(), nullable=True))
    op.add_column("form_versions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("form_versions", sa.Column("reviewer", sa.String(length=128), nullable=True))
    op.add_column("form_versions", sa.Column("warning", sa.Text(), nullable=True))

    op.create_table(
        "catalog_abuse_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reporter_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.add_column("documents", sa.Column("is_medical", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column(
        "documents",
        sa.Column("access_role", sa.String(length=64), server_default="standard", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("documents", "access_role")
    op.drop_column("documents", "is_medical")
    op.drop_table("catalog_abuse_reports")
    for col in (
        "warning",
        "reviewer",
        "reviewed_at",
        "valid_to",
        "valid_from",
        "act_title",
        "act_date",
        "act_number",
        "content_sha256",
        "source_snapshot_id",
    ):
        op.drop_column("form_versions", col)
    for col in ("authority", "region", "purpose", "organ"):
        op.drop_column("form_templates", col)
