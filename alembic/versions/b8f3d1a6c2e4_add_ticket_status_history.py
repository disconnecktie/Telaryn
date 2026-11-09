"""add ticket status history

Revision ID: b8f3d1a6c2e4
Revises: a4c9e2f7b1d3
Create Date: 2026-08-21 08:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8f3d1a6c2e4"
down_revision: Union[str, Sequence[str], None] = "a4c9e2f7b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_status_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=False),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_status_events_ticket_id"),
        "ticket_status_events",
        ["ticket_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ticket_status_events_ticket_id"),
        table_name="ticket_status_events",
    )
    op.drop_table("ticket_status_events")
