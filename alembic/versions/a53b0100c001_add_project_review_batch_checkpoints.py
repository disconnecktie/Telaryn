"""Add persisted Project Review batch checkpoints.

Revision ID: a53b0100c001
Revises: a82b0100c005
"""

from alembic import op
import sqlalchemy as sa


revision = "a53b0100c001"
down_revision = "a82b0100c005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_review_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("batch_index", sa.Integer(), nullable=False),
        sa.Column("ticket_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("safe_error_category", sa.String(length=50), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["project_review_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "batch_index", name="uq_project_review_batch_index"),
    )
    op.create_index("ix_project_review_batches_attempt_id", "project_review_batches", ["attempt_id"])
    op.create_index("ix_project_review_batch_resume", "project_review_batches", ["attempt_id", "status", "batch_index"])


def downgrade():
    op.drop_index("ix_project_review_batch_resume", table_name="project_review_batches")
    op.drop_index("ix_project_review_batches_attempt_id", table_name="project_review_batches")
    op.drop_table("project_review_batches")
