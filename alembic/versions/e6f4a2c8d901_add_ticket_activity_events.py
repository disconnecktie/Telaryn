"""add ticket activity events

Revision ID: e6f4a2c8d901
Revises: d3e7f9a1b5c8
Create Date: 2026-08-23 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f4a2c8d901"
down_revision: Union[str, Sequence[str], None] = "d3e7f9a1b5c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_activity_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_type", sa.String(length=30), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("field_name", sa.String(length=50), nullable=True),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_activity_events_ticket_id"),
        "ticket_activity_events",
        ["ticket_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ticket_activity_events_ticket_id"),
        table_name="ticket_activity_events",
    )
    op.drop_table("ticket_activity_events")
