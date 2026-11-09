"""add feedback retention anchor

Revision ID: a107b010c001
Revises: a102b010c001
"""

from alembic import op
import sqlalchemy as sa


revision = "a107b010c001"
down_revision = "a102b010c001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "feedback_submissions",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE feedback_submissions "
        "SET closed_at = COALESCE(reviewed_at, updated_at) "
        "WHERE status = 'closed'"
    )
    op.create_index(
        "ix_feedback_submissions_closed_at",
        "feedback_submissions",
        ["closed_at"],
    )


def downgrade():
    op.drop_index(
        "ix_feedback_submissions_closed_at",
        table_name="feedback_submissions",
    )
    op.drop_column("feedback_submissions", "closed_at")
