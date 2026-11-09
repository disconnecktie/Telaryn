"""Add account lifecycle state and deployment-administration audit events."""

from alembic import op
import sqlalchemy as sa


revision = "a82b0100c005"
down_revision = "a81b0400c004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("account_status", sa.String(20), nullable=False, server_default="active"))
        batch.add_column(sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint("ck_user_account_status", "account_status IN ('active', 'disabled')")
    op.create_table(
        "account_admin_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("affected_user_id", sa.Integer(), nullable=False),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["affected_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_admin_events_actor_id", "account_admin_events", ["actor_id"])
    op.create_index("ix_account_admin_events_affected_user_id", "account_admin_events", ["affected_user_id"])


def downgrade():
    op.drop_index("ix_account_admin_events_affected_user_id", table_name="account_admin_events")
    op.drop_index("ix_account_admin_events_actor_id", table_name="account_admin_events")
    op.drop_table("account_admin_events")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_user_account_status", type_="check")
        batch.drop_column("disabled_at")
        batch.drop_column("account_status")
