"""Add durable Project Review queue state.

Revision ID: a55b0100c003
Revises: a54b0100c002
"""

from alembic import op
import sqlalchemy as sa


revision = "a55b0100c003"
down_revision = "a54b0100c002"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE projectreviewattemptstatus ADD VALUE IF NOT EXISTS 'RUNNING'"
        )
    op.add_column(
        "project_review_attempts",
        sa.Column("review_reference", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "project_review_attempts",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    # PostgreSQL enum values are intentionally retained on downgrade.
    op.drop_column("project_review_attempts", "started_at")
    op.drop_column("project_review_attempts", "review_reference")
