"""Analysis pipeline versioning and page geometry.

Revision ID: 0004_analysis_pipeline
Revises: 0003_upload_lifecycle
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_analysis_pipeline"
down_revision: Union[str, None] = "0003_upload_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("pipeline_version", sa.String(length=64), nullable=True))
    op.add_column("analysis_runs", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("analysis_runs", sa.Column("schema_version", sa.String(length=64), nullable=True))
    op.add_column("analysis_runs", sa.Column("ocr_model_version", sa.String(length=64), nullable=True))
    op.add_column("analysis_runs", sa.Column("llm_model_version", sa.String(length=64), nullable=True))

    op.add_column("extracted_pages", sa.Column("width", sa.Float(), nullable=True))
    op.add_column("extracted_pages", sa.Column("height", sa.Float(), nullable=True))
    op.add_column(
        "extracted_pages",
        sa.Column("rotation", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("extracted_pages", sa.Column("language", sa.String(length=16), nullable=True))
    op.add_column("extracted_pages", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column("extracted_pages", sa.Column("error_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("extracted_pages", "error_code")
    op.drop_column("extracted_pages", "source")
    op.drop_column("extracted_pages", "language")
    op.drop_column("extracted_pages", "rotation")
    op.drop_column("extracted_pages", "height")
    op.drop_column("extracted_pages", "width")
    op.drop_column("analysis_runs", "llm_model_version")
    op.drop_column("analysis_runs", "ocr_model_version")
    op.drop_column("analysis_runs", "schema_version")
    op.drop_column("analysis_runs", "prompt_version")
    op.drop_column("analysis_runs", "pipeline_version")
