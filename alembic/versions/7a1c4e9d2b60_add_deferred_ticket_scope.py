"""add deferred ticket scope

Revision ID: 7a1c4e9d2b60
Revises: e6f4a2c8d901
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a1c4e9d2b60"
down_revision: Union[str, Sequence[str], None] = "e6f4a2c8d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "acceptance_criteria",
        sa.Column("deferred", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("acceptance_criteria", sa.Column("deferred_at", sa.DateTime(), nullable=True))
    op.add_column("acceptance_criteria", sa.Column("deferred_reason", sa.Text(), nullable=True))
    op.add_column("subtasks", sa.Column("deferred_at", sa.DateTime(), nullable=True))
    op.add_column("subtasks", sa.Column("deferred_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("subtasks", "deferred_reason")
    op.drop_column("subtasks", "deferred_at")
    op.drop_column("acceptance_criteria", "deferred_reason")
    op.drop_column("acceptance_criteria", "deferred_at")
    op.drop_column("acceptance_criteria", "deferred")
