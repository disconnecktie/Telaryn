"""Remove obsolete Project Review batch checkpoints.

Revision ID: a56b0100c004
Revises: a55b0100c003
"""

from alembic import op
import sqlalchemy as sa


revision = "a56b0100c004"
down_revision = "a55b0100c003"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("project_review_batches")


def downgrade():
    # Historical migration rollback must restore the schema expected by a53.
    # Atlas no longer has a runtime model or worker that uses this table.
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
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["project_review_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attempt_id",
            "batch_index",
            name="uq_project_review_batch_index",
        ),
    )
    op.create_index(
        "ix_project_review_batches_attempt_id",
        "project_review_batches",
        ["attempt_id"],
    )
    op.create_index(
        "ix_project_review_batch_resume",
        "project_review_batches",
        ["attempt_id", "status", "batch_index"],
    )
