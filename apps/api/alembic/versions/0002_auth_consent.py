"""Auth + consent schema extensions.

Revision ID: 0002_auth_consent
Revises: 0001_initial
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth_consent"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("sessions", sa.Column("rotated_from", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("sessions", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.add_column("sessions", sa.Column("ip", sa.String(length=64), nullable=True))

    op.add_column("legal_documents", sa.Column("canonical_text", sa.Text(), nullable=True))
    op.add_column("legal_documents", sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "legal_documents",
        sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("legal_documents.id"), nullable=True),
    )
    op.add_column("legal_documents", sa.Column("reviewer_id", sa.String(length=128), nullable=True))
    op.add_column(
        "legal_documents",
        sa.Column("publication_status", sa.String(length=32), server_default="draft", nullable=False),
    )
    op.execute("UPDATE legal_documents SET effective_at = effective_from WHERE effective_at IS NULL")
    op.execute("UPDATE legal_documents SET publication_status = 'published' WHERE review_status = 'approved'")

    op.add_column("consent_events", sa.Column("consent_id", sa.String(length=128), nullable=True))
    op.add_column("consent_events", sa.Column("consent_version", sa.String(length=64), nullable=True))
    op.add_column("consent_events", sa.Column("content_hash", sa.String(length=128), nullable=True))
    op.add_column(
        "consent_events",
        sa.Column("action", sa.String(length=16), server_default="accept", nullable=False),
    )
    op.add_column("consent_events", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consent_events", sa.Column("ip", sa.String(length=64), nullable=True))
    op.add_column("consent_events", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.add_column("consent_events", sa.Column("locale", sa.String(length=16), server_default="ru-RU", nullable=False))
    op.add_column("consent_events", sa.Column("request_id", sa.String(length=64), nullable=True))
    op.add_column(
        "consent_events",
        sa.Column("evidence_schema_version", sa.String(length=64), server_default="consent_evidence.v1", nullable=False),
    )
    op.execute("UPDATE consent_events SET occurred_at = accepted_at WHERE occurred_at IS NULL")

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Append-only protection for consent_events
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_consent_event_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'consent_events are append-only';
        END;
        $$ LANGUAGE plpgsql;
        """,
    )
    op.execute(
        """
        CREATE TRIGGER trg_consent_events_no_update
        BEFORE UPDATE OR DELETE ON consent_events
        FOR EACH ROW EXECUTE PROCEDURE prevent_consent_event_mutation();
        """,
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_consent_events_no_update ON consent_events")
    op.execute("DROP FUNCTION IF EXISTS prevent_consent_event_mutation()")
    op.drop_table("email_verification_tokens")

    op.drop_column("consent_events", "evidence_schema_version")
    op.drop_column("consent_events", "request_id")
    op.drop_column("consent_events", "locale")
    op.drop_column("consent_events", "user_agent")
    op.drop_column("consent_events", "ip")
    op.drop_column("consent_events", "occurred_at")
    op.drop_column("consent_events", "action")
    op.drop_column("consent_events", "content_hash")
    op.drop_column("consent_events", "consent_version")
    op.drop_column("consent_events", "consent_id")

    op.drop_column("legal_documents", "publication_status")
    op.drop_column("legal_documents", "reviewer_id")
    op.drop_column("legal_documents", "supersedes_id")
    op.drop_column("legal_documents", "effective_at")
    op.drop_column("legal_documents", "canonical_text")

    op.drop_column("sessions", "ip")
    op.drop_column("sessions", "user_agent")
    op.drop_column("sessions", "rotated_from")

    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_hash")
