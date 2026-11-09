"""Shorten preliminary public Ticket identifiers before release.

Revision ID: a28b0100c002
Revises: a28b0100c001
"""

from secrets import choice

from alembic import op
import sqlalchemy as sa


revision = "a28b0100c002"
down_revision = "a28b0100c001"
branch_labels = None
depends_on = None


def _public_id() -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "TKT-" + "".join(choice(alphabet) for _ in range(16))


def upgrade():
    bind = op.get_bind()
    # Ticket #28 has not been released yet, so replace only the preliminary
    # UUID-shaped values created by the first development migration.
    tickets = bind.execute(
        sa.text("SELECT id, public_id FROM tickets ORDER BY id")
    ).mappings()
    for ticket in tickets:
        if len(ticket["public_id"]) > 20:
            bind.execute(
                sa.text("UPDATE tickets SET public_id = :public_id WHERE id = :ticket_id"),
                {"public_id": _public_id(), "ticket_id": ticket["id"]},
            )

    with op.batch_alter_table("tickets") as batch:
        batch.alter_column(
            "public_id",
            existing_type=sa.String(length=40),
            type_=sa.String(length=20),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("tickets") as batch:
        batch.alter_column(
            "public_id",
            existing_type=sa.String(length=20),
            type_=sa.String(length=40),
            existing_nullable=False,
        )
