"""Persist each member's default project independently of Current Focus."""

from alembic import op
import sqlalchemy as sa

revision = "f3c79a04b201"
down_revision = "e1b2c3d4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workspace_memberships") as batch:
        batch.add_column(sa.Column("default_project_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_membership_default_project", "projects", ["default_project_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("workspace_memberships") as batch:
        batch.drop_constraint("fk_membership_default_project", type_="foreignkey")
        batch.drop_column("default_project_id")
