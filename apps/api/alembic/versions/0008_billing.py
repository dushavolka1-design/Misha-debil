"""Billing subscription enrichment.

Revision ID: 0008_billing
Revises: 0007_form_fill
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_billing"
down_revision: Union[str, None] = "0007_form_fill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("price_version", sa.String(length=64), nullable=False, server_default="unset"))
    op.add_column("subscriptions", sa.Column("amount_minor", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("subscriptions", sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"))
    op.add_column("subscriptions", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("subscriptions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("subscriptions", sa.Column("next_renewal_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "subscriptions",
        sa.Column("recurring_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("subscriptions", sa.Column("payment_method_ref", sa.String(length=128), nullable=True))
    op.add_column("subscriptions", sa.Column("dunning_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("subscriptions", sa.Column("trial_notice_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "payment_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscriptions.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("provider_payment_ref", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("receipt_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_attempts_idempotency"),
    )
    op.create_index("ix_payment_attempts_subscription_id", "payment_attempts", ["subscription_id"])
    op.create_index("ix_payment_attempts_user_id", "payment_attempts", ["user_id"])

    op.create_table(
        "payment_refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "payment_attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("payment_attempts.id"),
            nullable=False,
        ),
        sa.Column("provider_refund_ref", sa.String(length=128), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payment_refunds_payment_attempt_id", "payment_refunds", ["payment_attempt_id"])

    op.add_column("payment_events", sa.Column("raw_hash", sa.String(length=64), nullable=True))
    op.add_column("payment_events", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "payment_events",
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("payment_events", "processed")
    op.drop_column("payment_events", "occurred_at")
    op.drop_column("payment_events", "raw_hash")
    op.drop_index("ix_payment_refunds_payment_attempt_id", table_name="payment_refunds")
    op.drop_table("payment_refunds")
    op.drop_index("ix_payment_attempts_user_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_subscription_id", table_name="payment_attempts")
    op.drop_table("payment_attempts")
    for col in (
        "trial_notice_sent_at",
        "dunning_attempts",
        "payment_method_ref",
        "recurring_enabled",
        "next_renewal_at",
        "cancelled_at",
        "cancellation_at_period_end",
        "current_period_end",
        "trial_ends_at",
        "currency",
        "amount_minor",
        "price_version",
    ):
        op.drop_column("subscriptions", col)
