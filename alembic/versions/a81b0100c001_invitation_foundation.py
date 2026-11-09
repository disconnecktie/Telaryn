"""Add digest-only invitation lifecycle storage without enabling account creation."""

from alembic import op
import sqlalchemy as sa

revision = "a81b0100c001"
down_revision = "a78b0300c003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("workspace_invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("access_requests.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("inviter_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role = 'member'", name="ck_invitation_role"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'revoked', 'delivery_failed')", name="ck_invitation_status"),
        sa.CheckConstraint("generation > 0", name="ck_invitation_generation"),
    )
    op.create_index("ix_workspace_invitations_expires_at", "workspace_invitations", ["expires_at"])
    op.create_table("workspace_invitation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invitation_id", sa.Integer(), sa.ForeignKey("workspace_invitations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspace_invitation_events_invitation_id", "workspace_invitation_events", ["invitation_id"])


def downgrade():
    op.drop_table("workspace_invitation_events")
    op.drop_table("workspace_invitations")
