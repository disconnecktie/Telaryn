"""add ticket updates

Revision ID: d3e7f9a1b5c8
Revises: b8f3d1a6c2e4
Create Date: 2026-08-21 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e7f9a1b5c8"
down_revision: Union[str, Sequence[str], None] = "b8f3d1a6c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_update_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_update_entries_ticket_id"),
        "ticket_update_entries",
        ["ticket_id"],
        unique=False,
    )
    op.create_table(
        "ticket_update_attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("update_entry_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["update_entry_id"],
            ["ticket_update_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_ticket_update_attachments_update_entry_id"),
        "ticket_update_attachments",
        ["update_entry_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ticket_update_attachments_update_entry_id"),
        table_name="ticket_update_attachments",
    )
    op.drop_table("ticket_update_attachments")
    op.drop_index(
        op.f("ix_ticket_update_entries_ticket_id"),
        table_name="ticket_update_entries",
    )
    op.drop_table("ticket_update_entries")
