"""add workspace ownership foundation

Revision ID: 9c4a7d8e2b51
Revises: 7a1c4e9d2b60
Create Date: 2026-08-25

"""

from __future__ import annotations

import os
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4a7d8e2b51"
down_revision: Union[str, Sequence[str], None] = "7a1c4e9d2b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the private-workspace boundary and safely adopt legacy data."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])
    op.create_index("ix_workspace_memberships_workspace_id", "workspace_memberships", ["workspace_id"])

    # The existing local application has no identity records.  Its complete
    # history is therefore adopted by exactly one bootstrap workspace, never
    # exposed as shared or copied into any future user's workspace.
    owner_email = os.getenv("ATLAS_BOOTSTRAP_USER_EMAIL", "atlas.local@example.com")
    owner_name = os.getenv("ATLAS_BOOTSTRAP_USER_DISPLAY_NAME", "Local user")
    workspace_name = os.getenv("ATLAS_BOOTSTRAP_WORKSPACE_NAME", "Atlas Waypoint Workspace")
    op.execute(
        sa.text(
            "INSERT INTO users (id, email, display_name, created_at, updated_at) "
            "VALUES (1, :email, :display_name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(email=owner_email, display_name=owner_name)
    )
    op.execute(
        sa.text(
            "INSERT INTO workspaces (id, name, created_by_user_id, created_at, updated_at) "
            "VALUES (1, :name, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(name=workspace_name)
    )
    op.execute(
        sa.text(
            "INSERT INTO workspace_memberships (workspace_id, user_id, role, created_at) "
            "VALUES (1, 1, 'owner', CURRENT_TIMESTAMP)"
        )
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE projects SET workspace_id = 1 WHERE workspace_id IS NULL"))
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_projects_workspace_id", "workspaces", ["workspace_id"], ["id"])
        batch_op.create_index("ix_projects_workspace_id", ["workspace_id"], unique=False)

    with op.batch_alter_table("tickets") as batch_op:
        batch_op.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE tickets SET workspace_id = 1 WHERE workspace_id IS NULL"))
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key("fk_tickets_workspace_id", "workspaces", ["workspace_id"], ["id"])
        batch_op.create_index("ix_tickets_workspace_id", ["workspace_id"], unique=False)


def downgrade() -> None:
    """Remove the ownership foundation in reverse dependency order."""
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.drop_index("ix_tickets_workspace_id")
        batch_op.drop_constraint("fk_tickets_workspace_id", type_="foreignkey")
        batch_op.drop_column("workspace_id")
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_workspace_id")
        batch_op.drop_constraint("fk_projects_workspace_id", type_="foreignkey")
        batch_op.drop_column("workspace_id")
    op.drop_index("ix_workspace_memberships_workspace_id", table_name="workspace_memberships")
    op.drop_index("ix_workspace_memberships_user_id", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
