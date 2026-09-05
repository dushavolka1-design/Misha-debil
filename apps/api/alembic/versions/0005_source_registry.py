"""Official source registry fields.

Revision ID: 0005_source_registry
Revises: 0004_analysis_pipeline
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_source_registry"
down_revision: Union[str, None] = "0004_analysis_pipeline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("source_records", sa.Column("organ", sa.String(length=512), nullable=True))
    op.add_column("source_records", sa.Column("official_url", sa.String(length=1024), nullable=True))
    op.add_column("source_records", sa.Column("host", sa.String(length=255), nullable=True))
    op.add_column("source_records", sa.Column("criticality", sa.String(length=32), nullable=True))
    op.add_column("source_records", sa.Column("fetch_interval_hours", sa.Integer(), server_default="72", nullable=False))
    op.add_column("source_records", sa.Column("lifecycle_state", sa.String(length=32), server_default="discovered", nullable=False))

    op.add_column("source_snapshots", sa.Column("requested_url", sa.String(length=1024), nullable=True))
    op.add_column("source_snapshots", sa.Column("final_url", sa.String(length=1024), nullable=True))
    op.add_column("source_snapshots", sa.Column("lifecycle_state", sa.String(length=32), server_default="discovered", nullable=False))
    op.add_column("source_snapshots", sa.Column("parser_version", sa.String(length=64), nullable=True))
    op.add_column("source_snapshots", sa.Column("extracted_text", sa.Text(), nullable=True))
    op.add_column("source_snapshots", sa.Column("headers_json", sa.JSON(), nullable=True))
    op.add_column("source_snapshots", sa.Column("valid_from", sa.Date(), nullable=True))
    op.add_column("source_snapshots", sa.Column("valid_to", sa.Date(), nullable=True))
    op.add_column("source_snapshots", sa.Column("act_title", sa.String(length=512), nullable=True))
    op.add_column("source_snapshots", sa.Column("act_number", sa.String(length=128), nullable=True))
    op.add_column("source_snapshots", sa.Column("act_date", sa.Date(), nullable=True))
    op.add_column("source_snapshots", sa.Column("reviewer_id", sa.String(length=128), nullable=True))
    op.add_column("source_snapshots", sa.Column("review_comment", sa.Text(), nullable=True))
    op.add_column("source_snapshots", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("source_snapshots", sa.Column("link_status", sa.String(length=32), server_default="ok", nullable=False))
    op.add_column("source_snapshots", sa.Column("previous_snapshot_id", sa.UUID(), nullable=True))


def downgrade() -> None:
    for col in (
        "previous_snapshot_id",
        "link_status",
        "reviewed_at",
        "review_comment",
        "reviewer_id",
        "act_date",
        "act_number",
        "act_title",
        "valid_to",
        "valid_from",
        "headers_json",
        "extracted_text",
        "parser_version",
        "lifecycle_state",
        "final_url",
        "requested_url",
    ):
        op.drop_column("source_snapshots", col)
    for col in (
        "lifecycle_state",
        "fetch_interval_hours",
        "criticality",
        "host",
        "official_url",
        "organ",
    ):
        op.drop_column("source_records", col)
