"""Add reversible Project archival lifecycle state.

Revision ID: a39b0100c004
Revises: a28b0100c003
"""

from alembic import op
import sqlalchemy as sa


revision = "a39b0100c004"
down_revision = "a28b0100c003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        batch.add_column(
            sa.Column("archived_by_user_id", sa.Integer(), nullable=True)
        )
        batch.create_foreign_key(
            "fk_projects_archived_by_user_id_users",
            "users",
            ["archived_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_projects_archived_at", ["archived_at"])

    op.create_table(
        "project_lifecycle_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Integer(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_project_lifecycle_events_workspace_id",
        "project_lifecycle_events",
        ["workspace_id"],
    )
    op.create_index(
        "ix_project_lifecycle_events_project_id",
        "project_lifecycle_events",
        ["project_id"],
    )
    op.create_index(
        "ix_project_lifecycle_events_actor_user_id",
        "project_lifecycle_events",
        ["actor_user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_project_lifecycle_events_actor_user_id",
        table_name="project_lifecycle_events",
    )
    op.drop_index(
        "ix_project_lifecycle_events_project_id",
        table_name="project_lifecycle_events",
    )
    op.drop_index(
        "ix_project_lifecycle_events_workspace_id",
        table_name="project_lifecycle_events",
    )
    op.drop_table("project_lifecycle_events")
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_archived_at")
        batch.drop_constraint(
            "fk_projects_archived_by_user_id_users",
            type_="foreignkey",
        )
        batch.drop_column("archived_by_user_id")
        batch.drop_column("archived_at")
