"""Upload lifecycle columns + idempotent jobs.

Revision ID: 0003_upload_lifecycle
Revises: 0002_auth_consent
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_upload_lifecycle"
down_revision: Union[str, None] = "0002_auth_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("display_name", sa.String(length=512), nullable=True))
    op.add_column("documents", sa.Column("detected_type", sa.String(length=32), nullable=True))
    op.add_column("documents", sa.Column("error_code", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("documents", sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("tombstone_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "documents",
        sa.Column("legal_hold", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.alter_column(
        "documents",
        "status",
        server_default="CREATED",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_index("ix_documents_user_idempotency", "documents", ["user_id", "idempotency_key"])

    op.add_column("document_files", sa.Column("wrapped_dek", sa.Text(), nullable=True))
    op.add_column("document_files", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "upload_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="done", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("document_id", "job_id", name="uq_upload_job_idempotent"),
    )
    op.create_index("ix_upload_jobs_document_id", "upload_jobs", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_upload_jobs_document_id", table_name="upload_jobs")
    op.drop_table("upload_jobs")
    op.drop_column("document_files", "expires_at")
    op.drop_column("document_files", "wrapped_dek")
    op.drop_index("ix_documents_user_idempotency", table_name="documents")
    op.alter_column(
        "documents",
        "status",
        server_default="uploaded",
        existing_type=sa.String(length=32),
        existing_nullable=False,
    )
    op.drop_column("documents", "legal_hold")
    op.drop_column("documents", "tombstone_at")
    op.drop_column("documents", "retention_expires_at")
    op.drop_column("documents", "idempotency_key")
    op.drop_column("documents", "error_code")
    op.drop_column("documents", "detected_type")
    op.drop_column("documents", "display_name")
