"""Allow explicit fresh Project Review attempts.

Revision ID: a57b0100c005
Revises: a56b0100c004
"""

from alembic import op


revision = "a57b0100c005"
down_revision = "a56b0100c004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project_review_attempts") as batch_op:
        batch_op.drop_constraint(
            "uq_project_review_success_per_snapshot",
            type_="unique",
        )


def downgrade():
    with op.batch_alter_table("project_review_attempts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_project_review_success_per_snapshot",
            [
                "workspace_id",
                "project_id",
                "requested_by_user_id",
                "successful_snapshot_key",
            ],
        )
