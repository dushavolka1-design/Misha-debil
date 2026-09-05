"""Typed catalog_forms / fill runtime tables. Desktop uses SQL, not one JSON blob."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_form_catalog_sql"
down_revision = "0009_persistence_runtime"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=128), nullable=False, unique=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("organ", sa.String(length=256), nullable=False),
        sa.Column("purpose", sa.String(length=128), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False, server_default="RF"),
        sa.Column("authority", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("raw_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("act_number", sa.String(length=128), nullable=True),
        sa.Column("act_date", sa.Date(), nullable=True),
        sa.Column("act_title", sa.String(length=512), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer", sa.String(length=128), nullable=True),
        sa.Column("warning", sa.Text(), nullable=False, server_default=""),
        sa.Column("edition_note", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="entry_stay"),
        sa.Column("form_kind", sa.String(length=32), nullable=False, server_default="government_form"),
        sa.Column("fill_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fill_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "catalog_quarantine",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_key", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_catalog_quarantine_correlation_id", "catalog_quarantine", ["correlation_id"])
    op.create_table(
        "catalog_blob_backups",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("namespace", sa.String(length=64), nullable=False),
        sa.Column("blob_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "fill_runtime_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("form_version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("original_pdf", sa.LargeBinary(), nullable=False),
        sa.Column("original_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "page_geometry_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("coord_map_json", sa.Text(), nullable=False),
        sa.Column("coord_map_hash", sa.String(length=64), nullable=False),
        sa.Column("allowed_font_name", sa.String(length=128), nullable=False),
        sa.Column("allowed_font_hash", sa.String(length=64), nullable=False),
        sa.Column("font_license", sa.String(length=256), nullable=False, server_default=""),
        sa.Column(
            "field_schema_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("author_id", sa.String(length=128), nullable=False),
        sa.Column("catalog_form_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("second_reviewer_id", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fill_runtime_versions_catalog_form_id", "fill_runtime_versions", ["catalog_form_id"])
    op.create_table(
        "fill_runtime_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_form_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("form_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "answers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_fill_runtime_drafts_user_id", "fill_runtime_drafts", ["user_id"])
    op.create_index("ix_fill_runtime_drafts_catalog_form_id", "fill_runtime_drafts", ["catalog_form_id"])
    op.create_table(
        "fill_runtime_generated",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("form_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_form_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "answers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("template_hash", sa.String(length=64), nullable=False),
        sa.Column("coord_map_hash", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("output_pdf", sa.LargeBinary(), nullable=False),
        sa.Column(
            "preview_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "audit_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fill_runtime_generated_user_id", "fill_runtime_generated", ["user_id"])


def downgrade() -> None:
    op.drop_table("fill_runtime_generated")
    op.drop_table("fill_runtime_drafts")
    op.drop_table("fill_runtime_versions")
    op.drop_table("catalog_blob_backups")
    op.drop_table("catalog_quarantine")
    op.drop_table("catalog_forms")
