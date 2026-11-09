"""repair an explicitly approved fresh production bootstrap owner

Revision ID: a108b010c002
Revises: a107b010c001
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "a108b010c002"
down_revision = "a107b010c001"
branch_labels = None
depends_on = None


PLACEHOLDER_EMAIL = "atlas.local@example.com"
REPAIR_APPROVAL_ENV = "ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED"


def upgrade() -> None:
    """Repair only the exact placeholder state created on first production deploy."""
    if os.getenv("ENVIRONMENT") != "production":
        return

    expected_email = os.getenv("ATLAS_BOOTSTRAP_USER_EMAIL", "").strip().lower()
    if not expected_email or expected_email == PLACEHOLDER_EMAIL or "@" not in expected_email:
        raise RuntimeError(
            "Refusing production bootstrap repair without an explicit, "
            "non-placeholder ATLAS_BOOTSTRAP_USER_EMAIL."
        )

    connection = op.get_bind()
    users = connection.execute(
        sa.text("SELECT id, email, password_hash FROM users ORDER BY id")
    ).mappings().all()

    if any(str(user["email"]).lower() == expected_email for user in users):
        return
    if (
        len(users) != 1
        or str(users[0]["email"]).lower() != PLACEHOLDER_EMAIL
        or users[0]["password_hash"] is not None
    ):
        raise RuntimeError(
            "Refusing to repair an unexpected production identity state."
        )

    # The public source snapshot must not assume any particular deployment's
    # privileged address. An operator must explicitly authorize this one-time
    # repair before Alembic updates a placeholder user's identity.
    if os.getenv(REPAIR_APPROVAL_ENV, "").strip() != "yes":
        raise RuntimeError(
            "Refusing placeholder owner repair without explicit "
            "ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED=yes."
        )

    user_id = users[0]["id"]
    workspaces = connection.execute(
        sa.text(
            "SELECT id, name FROM workspaces "
            "WHERE created_by_user_id = :user_id ORDER BY id"
        ),
        {"user_id": user_id},
    ).mappings().all()
    memberships = connection.execute(
        sa.text(
            "SELECT workspace_id, role FROM workspace_memberships "
            "WHERE user_id = :user_id ORDER BY workspace_id"
        ),
        {"user_id": user_id},
    ).mappings().all()

    if (
        len(workspaces) != 1
        or len(memberships) != 1
        or memberships[0]["workspace_id"] != workspaces[0]["id"]
        or memberships[0]["role"] != "owner"
    ):
        raise RuntimeError(
            "Refusing to repair an unexpected production workspace state."
        )

    display_name = os.getenv(
        "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME", "Telaryn Administrator"
    )
    workspace_name = os.getenv(
        "ATLAS_BOOTSTRAP_WORKSPACE_NAME", "Telaryn Administration"
    )
    connection.execute(
        sa.text(
            "UPDATE users SET email = :email, display_name = :display_name, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = :user_id"
        ),
        {
            "email": expected_email,
            "display_name": display_name,
            "user_id": user_id,
        },
    )
    connection.execute(
        sa.text(
            "UPDATE workspaces SET name = :name, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :workspace_id"
        ),
        {"name": workspace_name, "workspace_id": workspaces[0]["id"]},
    )


def downgrade() -> None:
    """Do not turn a configured production administrator back into a placeholder."""

