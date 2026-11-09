"""Persist Private Ticket policy and local-only Project Review exclusions.

Revision ID: a83b0100c002
Revises: a83b0100c001
"""

from alembic import op
import sqlalchemy as sa


revision = "a83b0100c002"
down_revision = "a83b0100c001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tickets") as batch:
        batch.add_column(
            sa.Column(
                "ai_context_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
    with op.batch_alter_table("project_review_attempts") as batch:
        batch.add_column(
            sa.Column("excluded_private_tickets", sa.JSON(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("project_review_attempts") as batch:
        batch.drop_column("excluded_private_tickets")
    with op.batch_alter_table("tickets") as batch:
        batch.drop_column("ai_context_enabled")
