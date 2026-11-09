"""Bind authenticated sessions to one authorized workspace for invited users."""

from alembic import op
import sqlalchemy as sa

revision = "a81b0200c002"
down_revision = "a81b0100c001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("auth_sessions") as batch:
        batch.add_column(sa.Column("workspace_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_auth_session_workspace", "workspaces", ["workspace_id"], ["id"], ondelete="SET NULL")
    op.execute("""
        UPDATE auth_sessions
        SET workspace_id = (
            SELECT workspace_id FROM workspace_memberships
            WHERE workspace_memberships.user_id = auth_sessions.user_id
            ORDER BY workspace_memberships.id LIMIT 1
        )
    """)


def downgrade():
    with op.batch_alter_table("auth_sessions") as batch:
        batch.drop_constraint("fk_auth_session_workspace", type_="foreignkey")
        batch.drop_column("workspace_id")
