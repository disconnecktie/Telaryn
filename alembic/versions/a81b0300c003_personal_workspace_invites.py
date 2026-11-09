"""Make approved intake invitations provision a private owner workspace."""

from alembic import op
import sqlalchemy as sa

revision = "a81b0300c003"
down_revision = "a81b0200c002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workspace_invitations") as batch:
        batch.drop_constraint("ck_invitation_role", type_="check")
        batch.alter_column("workspace_id", existing_type=sa.Integer(), nullable=True)
        batch.create_check_constraint("ck_invitation_role", "role IN ('member', 'owner')")
    with op.batch_alter_table("workspace_invitation_events") as batch:
        batch.alter_column("workspace_id", existing_type=sa.Integer(), nullable=True)
    # Supersede unaccepted collaborator links created during local validation.
    # Accepted records remain intact as audit history and existing access is not revoked.
    op.execute("""
        UPDATE workspace_invitations
        SET workspace_id = NULL, role = 'owner', status = 'revoked', token_hash = NULL
        WHERE status IN ('pending', 'delivery_failed')
    """)


def downgrade():
    op.execute("DELETE FROM workspace_invitation_events WHERE workspace_id IS NULL")
    op.execute("DELETE FROM workspace_invitations WHERE workspace_id IS NULL")
    with op.batch_alter_table("workspace_invitation_events") as batch:
        batch.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("workspace_invitations") as batch:
        batch.drop_constraint("ck_invitation_role", type_="check")
        batch.alter_column("workspace_id", existing_type=sa.Integer(), nullable=False)
        batch.create_check_constraint("ck_invitation_role", "role = 'member'")
