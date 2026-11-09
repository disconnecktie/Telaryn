"""Add durable asynchronous Work Intake attempts.

Revision ID: a40b0100c005
Revises: a39b0100c004
"""

from alembic import op
import sqlalchemy as sa


revision = "a40b0100c005"
down_revision = "a39b0100c004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_intake_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("safe_error_category", sa.String(length=50), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_intake_attempts_workspace_id", "work_intake_attempts", ["workspace_id"])
    op.create_index("ix_work_intake_attempts_requested_by_user_id", "work_intake_attempts", ["requested_by_user_id"])
    op.create_index(
        "ix_work_intake_owner_current",
        "work_intake_attempts",
        ["workspace_id", "requested_by_user_id", "dismissed_at", "created_at"],
    )


def downgrade():
    op.drop_index("ix_work_intake_owner_current", table_name="work_intake_attempts")
    op.drop_index("ix_work_intake_attempts_requested_by_user_id", table_name="work_intake_attempts")
    op.drop_index("ix_work_intake_attempts_workspace_id", table_name="work_intake_attempts")
    op.drop_table("work_intake_attempts")
