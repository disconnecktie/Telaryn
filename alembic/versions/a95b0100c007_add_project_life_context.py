"""Add explicit user-controlled Project life context.

Revision ID: a95b0100c007
Revises: a94b0100c006
"""

from alembic import op
import sqlalchemy as sa


revision = "a95b0100c007"
down_revision = "a94b0100c006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column(
                "life_context",
                sa.String(length=20),
                nullable=False,
                server_default="unclassified",
            )
        )
        batch.create_check_constraint(
            "ck_projects_life_context",
            "life_context IN ('work', 'volunteer', 'personal', 'unclassified')",
        )
    with op.batch_alter_table("project_lifecycle_events") as batch:
        batch.add_column(sa.Column("previous_life_context", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("new_life_context", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("project_lifecycle_events") as batch:
        batch.drop_column("new_life_context")
        batch.drop_column("previous_life_context")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_life_context", type_="check")
        batch.drop_column("life_context")
