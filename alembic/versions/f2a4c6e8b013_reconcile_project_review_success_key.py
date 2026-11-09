"""Reconcile Project Review success-key schema applied during development.

Revision ID: f2a4c6e8b013
Revises: c7d2e4f8a910
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a4c6e8b013"
down_revision: Union[str, Sequence[str], None] = "c7d2e4f8a910"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bring early-applied development databases to the committed c7 schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("project_review_attempts")
    }

    # PR #68 briefly exposed this revision before its concurrency key was final.
    # Inspect first so fresh databases, which already received the final c7
    # schema, pass through this reconciliation without destructive table work.
    if "successful_snapshot_key" not in columns:
        with op.batch_alter_table("project_review_attempts") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "successful_snapshot_key",
                    sa.String(length=64),
                    nullable=True,
                )
            )

    inspector = sa.inspect(bind)
    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(
            "project_review_attempts"
        )
    }
    if "uq_project_review_success_per_snapshot" not in unique_constraints:
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

    inspector = sa.inspect(bind)
    indexes = {
        index["name"]
        for index in inspector.get_indexes("project_review_attempts")
    }
    if "ix_project_review_success_lookup" not in indexes:
        op.create_index(
            "ix_project_review_success_lookup",
            "project_review_attempts",
            [
                "workspace_id",
                "project_id",
                "requested_by_user_id",
                "snapshot_version",
                "status",
            ],
        )


def downgrade() -> None:
    """Keep the schema declared by c7 when returning to that revision."""
    # The parent revision's committed contract includes these objects. Removing
    # them here would make a database at c7 disagree with c7's migration file.
    pass
