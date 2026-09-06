"""Form fill pixel-perfect metadata.

Revision ID: 0007_form_fill
Revises: 0006_forms_medical
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_form_fill"
down_revision: Union[str, None] = "0006_forms_medical"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("form_versions", sa.Column("original_hash", sa.String(length=64), nullable=True))
    op.add_column("form_versions", sa.Column("coord_map_version", sa.String(length=64), nullable=True))
    op.add_column("form_versions", sa.Column("coord_map_hash", sa.String(length=64), nullable=True))
    op.add_column("form_versions", sa.Column("coord_map_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("form_versions", sa.Column("page_geometry_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("form_versions", sa.Column("allowed_font_hash", sa.String(length=64), nullable=True))
    op.add_column("form_versions", sa.Column("font_license", sa.String(length=256), nullable=True))
    op.add_column("form_versions", sa.Column("author_id", sa.String(length=128), nullable=True))
    op.add_column("form_versions", sa.Column("second_reviewer_id", sa.String(length=128), nullable=True))
    op.add_column("form_versions", sa.Column("blocked_reason", sa.Text(), nullable=True))

    op.add_column("generated_forms", sa.Column("template_hash", sa.String(length=64), nullable=True))
    op.add_column("generated_forms", sa.Column("coord_map_hash", sa.String(length=64), nullable=True))
    op.add_column("generated_forms", sa.Column("input_hash", sa.String(length=64), nullable=True))
    op.add_column("generated_forms", sa.Column("output_hash", sa.String(length=64), nullable=True))
    op.add_column("generated_forms", sa.Column("engine_version", sa.String(length=64), nullable=True))
    op.add_column("generated_forms", sa.Column("audit_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    for col in ("audit_json", "engine_version", "output_hash", "input_hash", "coord_map_hash", "template_hash"):
        op.drop_column("generated_forms", col)
    for col in (
        "blocked_reason",
        "second_reviewer_id",
        "author_id",
        "font_license",
        "allowed_font_hash",
        "page_geometry_json",
        "coord_map_json",
        "coord_map_hash",
        "coord_map_version",
        "original_hash",
    ):
        op.drop_column("form_versions", col)
