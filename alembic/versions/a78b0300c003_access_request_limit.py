"""Seed a shared bounded intake counter without recording visitor network identity."""

from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

revision = "a78b0300c003"
down_revision = "a78b0200c002"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "access_request_limit",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted", sa.Integer(), nullable=False),
    )
    op.bulk_insert(table, [{"id": 1, "window_start": datetime(2000, 1, 1, tzinfo=timezone.utc), "accepted": 0}])


def downgrade():
    op.drop_table("access_request_limit")
