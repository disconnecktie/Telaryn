"""add per-user workspace onboarding visibility

Revision ID: a109b010c003
Revises: a108b010c002
"""

from alembic import op
import sqlalchemy as sa

revision = "a109b010c003"
down_revision = "a108b010c002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "workspace_id", name="uq_onboarding_state_user_workspace"),
    )
    op.create_index("ix_onboarding_states_user_id", "onboarding_states", ["user_id"])
    op.create_index("ix_onboarding_states_workspace_id", "onboarding_states", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_onboarding_states_workspace_id", table_name="onboarding_states")
    op.drop_index("ix_onboarding_states_user_id", table_name="onboarding_states")
    op.drop_table("onboarding_states")
