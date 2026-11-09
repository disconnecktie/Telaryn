"""Persist human decisions on Project Review proposals.

Revision ID: a9d3e7c1b542
Revises: f2a4c6e8b013
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9d3e7c1b542"
down_revision: Union[str, Sequence[str], None] = "f2a4c6e8b013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_review_proposal_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_attempt_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("decided_by_user_id", sa.Integer(), nullable=False),
        sa.Column("proposal_index", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("edited_changes", sa.JSON(), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["review_attempt_id"], ["project_review_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_attempt_id",
            "proposal_index",
            name="uq_project_review_proposal_decision",
        ),
    )
    op.create_index(
        "ix_project_review_proposal_decisions_review_attempt_id",
        "project_review_proposal_decisions",
        ["review_attempt_id"],
    )
    op.create_index(
        "ix_project_review_proposal_decisions_workspace_id",
        "project_review_proposal_decisions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_project_review_proposal_decisions_project_id",
        "project_review_proposal_decisions",
        ["project_id"],
    )
    op.create_index(
        "ix_project_review_proposal_decisions_decided_by_user_id",
        "project_review_proposal_decisions",
        ["decided_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_review_proposal_decisions_decided_by_user_id", table_name="project_review_proposal_decisions")
    op.drop_index("ix_project_review_proposal_decisions_project_id", table_name="project_review_proposal_decisions")
    op.drop_index("ix_project_review_proposal_decisions_workspace_id", table_name="project_review_proposal_decisions")
    op.drop_index("ix_project_review_proposal_decisions_review_attempt_id", table_name="project_review_proposal_decisions")
    op.drop_table("project_review_proposal_decisions")
