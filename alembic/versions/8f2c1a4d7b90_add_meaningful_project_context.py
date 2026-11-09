"""Add meaningful project context.

Revision ID: 8f2c1a4d7b90
Revises: 6d3b9a2f8c10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f2c1a4d7b90"
down_revision: Union[str, Sequence[str], None] = "6d3b9a2f8c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("purpose", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("why_it_matters", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("target_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "target_date")
    op.drop_column("projects", "why_it_matters")
    op.drop_column("projects", "purpose")
