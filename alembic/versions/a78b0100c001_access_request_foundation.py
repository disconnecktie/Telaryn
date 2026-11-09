"""Add isolated access-request storage without enabling public collection."""

from alembic import op
import sqlalchemy as sa

revision = "a78b0100c001"
down_revision = "f3c79a04b201"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "access_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("biography", sa.Text(), nullable=False),
        sa.Column("referral_source", sa.String(20), nullable=False),
        sa.Column("referral_detail", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('new', 'reviewed', 'approved', 'declined', 'closed')", name="ck_access_request_status"),
    )
    op.create_index("ix_access_requests_expires_at", "access_requests", ["expires_at"])


def downgrade():
    # Destructive rollback removes intake records, never accounts or workspace data.
    op.drop_index("ix_access_requests_expires_at", table_name="access_requests")
    op.drop_table("access_requests")
