"""Add Project and child-work collaboration references.

Revision ID: a28b0100c003
Revises: a28b0100c002
"""

from secrets import choice

from alembic import op
import sqlalchemy as sa


revision = "a28b0100c003"
down_revision = "a28b0100c002"
branch_labels = None
depends_on = None

_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _public_id(prefix: str) -> str:
    groups = ["".join(choice(_ALPHABET) for _ in range(4)) for _ in range(3)]
    return f"{prefix}-{'-'.join(groups)}"


def _backfill_child_numbers(bind, table: str, counter_column: str) -> None:
    ticket_next_numbers = {
        ticket_id: 1
        for ticket_id in bind.execute(sa.text("SELECT id FROM tickets ORDER BY id")).scalars()
    }
    rows = bind.execute(
        sa.text(f"SELECT id, ticket_id FROM {table} ORDER BY ticket_id, id")
    ).mappings()
    for row in rows:
        number = ticket_next_numbers[row["ticket_id"]]
        ticket_next_numbers[row["ticket_id"]] = number + 1
        bind.execute(
            sa.text(f"UPDATE {table} SET reference_number = :number WHERE id = :id"),
            {"number": number, "id": row["id"]},
        )
    for ticket_id, next_number in ticket_next_numbers.items():
        bind.execute(
            sa.text(f"UPDATE tickets SET {counter_column} = :next_number WHERE id = :ticket_id"),
            {"next_number": next_number, "ticket_id": ticket_id},
        )


def upgrade():
    # Add nullable fields first, then backfill before installing permanent constraints.
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(sa.Column("next_project_number", sa.Integer(), nullable=False, server_default="1"))
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("public_id", sa.String(length=18), nullable=True))
        batch.add_column(sa.Column("workspace_project_number", sa.Integer(), nullable=True))
    with op.batch_alter_table("tickets") as batch:
        batch.add_column(sa.Column("next_acceptance_criterion_number", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("next_subtask_number", sa.Integer(), nullable=False, server_default="1"))
        batch.alter_column("public_id", existing_type=sa.String(length=20), type_=sa.String(length=18), existing_nullable=False)
    with op.batch_alter_table("acceptance_criteria") as batch:
        batch.add_column(sa.Column("reference_number", sa.Integer(), nullable=True))
    with op.batch_alter_table("subtasks") as batch:
        batch.add_column(sa.Column("reference_number", sa.Integer(), nullable=True))

    bind = op.get_bind()
    workspace_next_numbers = {
        workspace_id: 1
        for workspace_id in bind.execute(sa.text("SELECT id FROM workspaces ORDER BY id")).scalars()
    }
    projects = bind.execute(
        sa.text("SELECT id, workspace_id FROM projects ORDER BY workspace_id, id")
    ).mappings()
    for project in projects:
        number = workspace_next_numbers[project["workspace_id"]]
        workspace_next_numbers[project["workspace_id"]] = number + 1
        bind.execute(
            sa.text("UPDATE projects SET public_id = :public_id, workspace_project_number = :number WHERE id = :id"),
            {"public_id": _public_id("PRJ"), "number": number, "id": project["id"]},
        )
    for workspace_id, next_number in workspace_next_numbers.items():
        bind.execute(
            sa.text("UPDATE workspaces SET next_project_number = :next_number WHERE id = :workspace_id"),
            {"workspace_id": workspace_id, "next_number": next_number},
        )

    # Ticket #28 has not been released. Convert preliminary IDs to the grouped format.
    for ticket_id in bind.execute(sa.text("SELECT id FROM tickets ORDER BY id")).scalars():
        bind.execute(
            sa.text("UPDATE tickets SET public_id = :public_id WHERE id = :id"),
            {"public_id": _public_id("TKT"), "id": ticket_id},
        )

    _backfill_child_numbers(bind, "acceptance_criteria", "next_acceptance_criterion_number")
    _backfill_child_numbers(bind, "subtasks", "next_subtask_number")

    with op.batch_alter_table("projects") as batch:
        batch.alter_column("public_id", nullable=False)
        batch.alter_column("workspace_project_number", nullable=False)
        batch.create_unique_constraint("uq_projects_public_id", ["public_id"])
        batch.create_unique_constraint("uq_projects_workspace_project_number", ["workspace_id", "workspace_project_number"])
    with op.batch_alter_table("acceptance_criteria") as batch:
        batch.alter_column("reference_number", nullable=False)
        batch.create_unique_constraint("uq_acceptance_criteria_ticket_reference_number", ["ticket_id", "reference_number"])
    with op.batch_alter_table("subtasks") as batch:
        batch.alter_column("reference_number", nullable=False)
        batch.create_unique_constraint("uq_subtasks_ticket_reference_number", ["ticket_id", "reference_number"])


def downgrade():
    with op.batch_alter_table("subtasks") as batch:
        batch.drop_constraint("uq_subtasks_ticket_reference_number", type_="unique")
        batch.drop_column("reference_number")
    with op.batch_alter_table("acceptance_criteria") as batch:
        batch.drop_constraint("uq_acceptance_criteria_ticket_reference_number", type_="unique")
        batch.drop_column("reference_number")
    with op.batch_alter_table("tickets") as batch:
        batch.alter_column("public_id", existing_type=sa.String(length=18), type_=sa.String(length=20), existing_nullable=False)
        batch.drop_column("next_subtask_number")
        batch.drop_column("next_acceptance_criterion_number")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("uq_projects_workspace_project_number", type_="unique")
        batch.drop_constraint("uq_projects_public_id", type_="unique")
        batch.drop_column("workspace_project_number")
        batch.drop_column("public_id")
    with op.batch_alter_table("workspaces") as batch:
        batch.drop_column("next_project_number")
