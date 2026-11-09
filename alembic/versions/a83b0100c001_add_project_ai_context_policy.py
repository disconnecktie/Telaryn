"""Persist project AI-context policy and immutable policy-change metadata.

Revision ID: a83b0100c001
Revises: a57b0100c005
"""

from alembic import op
import sqlalchemy as sa


revision = "a83b0100c001"
down_revision = "a57b0100c005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(
            sa.Column(
                "ai_context_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
    op.create_table(
        "project_ai_policy_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("previous_ai_context_enabled", sa.Boolean(), nullable=False),
        sa.Column("new_ai_context_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_ai_policy_events_workspace_id",
        "project_ai_policy_events",
        ["workspace_id"],
    )
    op.create_index(
        "ix_project_ai_policy_events_project_id",
        "project_ai_policy_events",
        ["project_id"],
    )
    op.create_index(
        "ix_project_ai_policy_events_actor_id",
        "project_ai_policy_events",
        ["actor_id"],
    )


def downgrade():
    op.drop_index(
        "ix_project_ai_policy_events_actor_id",
        table_name="project_ai_policy_events",
    )
    op.drop_index(
        "ix_project_ai_policy_events_project_id",
        table_name="project_ai_policy_events",
    )
    op.drop_index(
        "ix_project_ai_policy_events_workspace_id",
        table_name="project_ai_policy_events",
    )
    op.drop_table("project_ai_policy_events")
    with op.batch_alter_table("projects") as batch:
        batch.drop_column("ai_context_enabled")
