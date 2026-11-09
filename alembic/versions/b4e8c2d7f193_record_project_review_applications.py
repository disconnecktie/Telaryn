"""Record atomic Project Review applications.

Revision ID: b4e8c2d7f193
Revises: a9d3e7c1b542
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8c2d7f193"
down_revision: Union[str, Sequence[str], None] = "a9d3e7c1b542"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_review_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_attempt_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("applied_by_user_id", sa.Integer(), nullable=False),
        sa.Column("proposal_indexes", sa.JSON(), nullable=False),
        sa.Column("resulting_changes", sa.JSON(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["review_attempt_id"], ["project_review_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["applied_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_review_applications_review_attempt_id", "project_review_applications", ["review_attempt_id"])
    op.create_index("ix_project_review_applications_workspace_id", "project_review_applications", ["workspace_id"])
    op.create_index("ix_project_review_applications_project_id", "project_review_applications", ["project_id"])
    op.create_index("ix_project_review_applications_applied_by_user_id", "project_review_applications", ["applied_by_user_id"])
    with op.batch_alter_table("project_review_proposal_decisions") as batch_op:
        batch_op.add_column(sa.Column("application_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_project_review_decision_application",
            "project_review_applications",
            ["application_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_project_review_proposal_decisions_application_id",
            ["application_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("project_review_proposal_decisions") as batch_op:
        batch_op.drop_index("ix_project_review_proposal_decisions_application_id")
        batch_op.drop_constraint("fk_project_review_decision_application", type_="foreignkey")
        batch_op.drop_column("application_id")
    op.drop_index("ix_project_review_applications_applied_by_user_id", table_name="project_review_applications")
    op.drop_index("ix_project_review_applications_project_id", table_name="project_review_applications")
    op.drop_index("ix_project_review_applications_workspace_id", table_name="project_review_applications")
    op.drop_index("ix_project_review_applications_review_attempt_id", table_name="project_review_applications")
    op.drop_table("project_review_applications")
