"""Add durable Project Review attempts.

Revision ID: c7d2e4f8a910
Revises: b4a6f8c2d190
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d2e4f8a910"
down_revision: Union[str, Sequence[str], None] = "b4a6f8c2d190"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_review_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_version", sa.String(length=64), nullable=False),
        sa.Column("successful_snapshot_key", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "COMPLETED", "FAILED", "TIMED_OUT", "INVALID", name="projectreviewattemptstatus"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("safe_error_category", sa.String(length=50), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "requested_by_user_id",
            "successful_snapshot_key",
            name="uq_project_review_success_per_snapshot",
        ),
    )
    op.create_index("ix_project_review_attempts_workspace_id", "project_review_attempts", ["workspace_id"])
    op.create_index("ix_project_review_attempts_project_id", "project_review_attempts", ["project_id"])
    op.create_index("ix_project_review_attempts_requested_by_user_id", "project_review_attempts", ["requested_by_user_id"])
    op.create_index(
        "ix_project_review_success_lookup",
        "project_review_attempts",
        ["workspace_id", "project_id", "requested_by_user_id", "snapshot_version", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_review_success_lookup", table_name="project_review_attempts")
    op.drop_index("ix_project_review_attempts_requested_by_user_id", table_name="project_review_attempts")
    op.drop_index("ix_project_review_attempts_project_id", table_name="project_review_attempts")
    op.drop_index("ix_project_review_attempts_workspace_id", table_name="project_review_attempts")
    op.drop_table("project_review_attempts")
