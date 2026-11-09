"""Record provider-neutral invitation delivery outcomes."""

from alembic import op
import sqlalchemy as sa

revision = "a81b0400c004"
down_revision = "a81b0300c003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workspace_invitations") as batch:
        batch.add_column(sa.Column("delivery_provider", sa.String(30), nullable=True))
        batch.add_column(sa.Column("delivery_message_id", sa.String(255), nullable=True))
        batch.add_column(sa.Column("delivery_attempted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("workspace_invitations") as batch:
        batch.drop_column("delivered_at")
        batch.drop_column("delivery_attempted_at")
        batch.drop_column("delivery_message_id")
        batch.drop_column("delivery_provider")
