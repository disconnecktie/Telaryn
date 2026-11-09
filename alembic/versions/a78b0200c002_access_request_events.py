"""Record private intake status changes with history deleted alongside requests."""

from alembic import op
import sqlalchemy as sa

revision = "a78b0200c002"
down_revision = "a78b0100c001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_request_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("access_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_access_request_events_request_id", "access_request_events", ["request_id"])


def downgrade():
    op.drop_index("ix_access_request_events_request_id", table_name="access_request_events")
    op.drop_table("access_request_events")
