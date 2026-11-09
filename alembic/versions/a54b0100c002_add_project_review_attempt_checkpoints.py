"""Add immutable Project Review token and snapshot checkpoints.

Revision ID: a54b0100c002
Revises: a53b0100c001
"""

from alembic import op
import sqlalchemy as sa


revision = "a54b0100c002"
down_revision = "a53b0100c001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project_review_attempts",
        sa.Column("snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "project_review_attempts",
        sa.Column("context_window_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_review_attempts",
        sa.Column("max_output_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_review_attempts",
        sa.Column("token_safety_margin", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_review_attempts",
        sa.Column("token_encoding", sa.String(length=100), nullable=True),
    )


def downgrade():
    op.drop_column("project_review_attempts", "token_encoding")
    op.drop_column("project_review_attempts", "token_safety_margin")
    op.drop_column("project_review_attempts", "max_output_tokens")
    op.drop_column("project_review_attempts", "context_window_tokens")
    op.drop_column("project_review_attempts", "snapshot")
