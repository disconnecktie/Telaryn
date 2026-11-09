"""Track acted-on Project Review focus recommendations.

Revision ID: c6f1a4d9e205
Revises: b4e8c2d7f193
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6f1a4d9e205"
down_revision: Union[str, Sequence[str], None] = "b4e8c2d7f193"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("project_review_proposal_decisions") as batch_op:
        batch_op.add_column(sa.Column("focus_applied_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("focus_previous_ticket_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("project_review_proposal_decisions") as batch_op:
        batch_op.drop_column("focus_previous_ticket_id")
        batch_op.drop_column("focus_applied_at")
