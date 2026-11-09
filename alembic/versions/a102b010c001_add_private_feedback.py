"""add private feedback

Revision ID: a102b010c001
Revises: a96b0100c008
"""
from alembic import op
import sqlalchemy as sa


revision = "a102b010c001"
down_revision = "a96b0100c008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=18), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("route", sa.String(length=500), nullable=False),
        sa.Column("app_version", sa.String(length=50), nullable=False),
        sa.Column("viewport_width", sa.Integer(), nullable=True),
        sa.Column("viewport_height", sa.Integer(), nullable=True),
        sa.Column("browser_context", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="new", nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("screenshot_data", sa.LargeBinary(), nullable=True),
        sa.Column("screenshot_content_type", sa.String(length=50), nullable=True),
        sa.Column("screenshot_filename", sa.String(length=255), nullable=True),
        sa.Column("screenshot_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("category IN ('problem', 'suggestion', 'other')", name="ck_feedback_category"),
        sa.CheckConstraint("status IN ('new', 'reviewing', 'resolved', 'closed')", name="ck_feedback_status"),
        sa.UniqueConstraint("public_id", name="uq_feedback_submissions_public_id"),
    )
    op.create_index("ix_feedback_submissions_submitted_by_user_id", "feedback_submissions", ["submitted_by_user_id"])
    op.create_index("ix_feedback_submissions_workspace_id", "feedback_submissions", ["workspace_id"])
    op.create_table(
        "feedback_admin_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("feedback_id", sa.Integer(), sa.ForeignKey("feedback_submissions.id"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("notes_changed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_admin_events_feedback_id", "feedback_admin_events", ["feedback_id"])
    op.create_index("ix_feedback_admin_events_actor_id", "feedback_admin_events", ["actor_id"])


def downgrade():
    op.drop_index("ix_feedback_admin_events_actor_id", table_name="feedback_admin_events")
    op.drop_index("ix_feedback_admin_events_feedback_id", table_name="feedback_admin_events")
    op.drop_table("feedback_admin_events")
    op.drop_index("ix_feedback_submissions_workspace_id", table_name="feedback_submissions")
    op.drop_index("ix_feedback_submissions_submitted_by_user_id", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")

