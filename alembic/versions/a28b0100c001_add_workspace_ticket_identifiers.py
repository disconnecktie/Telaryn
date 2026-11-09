"""Add workspace-local Ticket numbers and immutable public identifiers.

Revision ID: a28b0100c001
Revises: a83b0100c002
"""

from secrets import choice

from alembic import op
import sqlalchemy as sa


revision = "a28b0100c001"
down_revision = "a83b0100c002"
branch_labels = None
depends_on = None


def _public_id() -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "TKT-" + "".join(choice(alphabet) for _ in range(16))


def upgrade():
    # Add nullable columns first so every existing database can be backfilled
    # before the permanent uniqueness and non-null guarantees are installed.
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(
            sa.Column(
                "next_ticket_number",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
    with op.batch_alter_table("tickets") as batch:
        batch.add_column(sa.Column("public_id", sa.String(length=20), nullable=True))
        batch.add_column(
            sa.Column("workspace_ticket_number", sa.Integer(), nullable=True)
        )

    bind = op.get_bind()
    workspace_next_numbers = {
        workspace_id: 1
        for workspace_id in bind.execute(
            sa.text("SELECT id FROM workspaces ORDER BY id")
        ).scalars()
    }
    tickets = bind.execute(
        sa.text("SELECT id, workspace_id FROM tickets ORDER BY workspace_id, id")
    ).mappings()

    for ticket in tickets:
        number = workspace_next_numbers[ticket["workspace_id"]]
        workspace_next_numbers[ticket["workspace_id"]] = number + 1
        bind.execute(
            sa.text(
                "UPDATE tickets "
                "SET public_id = :public_id, workspace_ticket_number = :number "
                "WHERE id = :ticket_id"
            ),
            {
                "public_id": _public_id(),
                "number": number,
                "ticket_id": ticket["id"],
            },
        )

    for workspace_id, next_number in workspace_next_numbers.items():
        bind.execute(
            sa.text(
                "UPDATE workspaces SET next_ticket_number = :next_number "
                "WHERE id = :workspace_id"
            ),
            {"workspace_id": workspace_id, "next_number": next_number},
        )

    with op.batch_alter_table("tickets") as batch:
        batch.alter_column("public_id", nullable=False)
        batch.alter_column("workspace_ticket_number", nullable=False)
        batch.create_unique_constraint("uq_tickets_public_id", ["public_id"])
        batch.create_unique_constraint(
            "uq_tickets_workspace_ticket_number",
            ["workspace_id", "workspace_ticket_number"],
        )


def downgrade():
    with op.batch_alter_table("tickets") as batch:
        batch.drop_constraint("uq_tickets_workspace_ticket_number", type_="unique")
        batch.drop_constraint("uq_tickets_public_id", type_="unique")
        batch.drop_column("workspace_ticket_number")
        batch.drop_column("public_id")
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("next_ticket_number")
