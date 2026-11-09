"""Add user-specific My Work focus preferences.

Revision ID: b4a6f8c2d190
Revises: 8f2c1a4d7b90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4a6f8c2d190"
down_revision: Union[str, Sequence[str], None] = "8f2c1a4d7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "my_work_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("is_current_focus", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "availability_mode",
            sa.Enum("AVAILABLE", "DATE", "CONTEXT_CHANGE", "MANUAL", name="focusavailabilitymode"),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column("available_on", sa.Date(), nullable=True),
        sa.Column("context_ticket_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "workspace_id",
            "ticket_id",
            name="uq_my_work_preference_owner_ticket",
        ),
    )
    op.create_index("ix_my_work_preferences_user_id", "my_work_preferences", ["user_id"])
    op.create_index("ix_my_work_preferences_workspace_id", "my_work_preferences", ["workspace_id"])
    op.create_index("ix_my_work_preferences_ticket_id", "my_work_preferences", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_my_work_preferences_ticket_id", table_name="my_work_preferences")
    op.drop_index("ix_my_work_preferences_workspace_id", table_name="my_work_preferences")
    op.drop_index("ix_my_work_preferences_user_id", table_name="my_work_preferences")
    op.drop_table("my_work_preferences")
