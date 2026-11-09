"""add projects

Revision ID: c01d1be2ce40
Revises: 59dedefb3aac
Create Date: 2026-08-16 21:19:41.935709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c01d1be2ce40'
down_revision: Union[str, Sequence[str], None] = '59dedefb3aac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("tickets") as batch_op:
        batch_op.add_column(
            sa.Column("project_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_tickets_project_id_projects",
            "projects",
            ["project_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.drop_constraint(
            "fk_tickets_project_id_projects",
            type_="foreignkey",
        )
        batch_op.drop_column("project_id")

    op.drop_table("projects")
