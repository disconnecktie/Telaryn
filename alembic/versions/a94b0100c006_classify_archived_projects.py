"""Classify archived Projects and preserve archive reasons in lifecycle history.

Revision ID: a94b0100c006
Revises: a40b0100c005
"""

from alembic import op
import sqlalchemy as sa


revision = "a94b0100c006"
down_revision = "a40b0100c005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("archive_reason", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("archive_reason_note", sa.Text(), nullable=True))
        batch.create_check_constraint(
            "ck_projects_archive_reason",
            "archive_reason IS NULL OR archive_reason IN "
            "('completed', 'superseded', 'cancelled', 'test_development', 'other')",
        )
    with op.batch_alter_table("project_lifecycle_events") as batch:
        batch.add_column(sa.Column("archive_reason", sa.String(length=32), nullable=True))
        batch.add_column(sa.Column("archive_reason_note", sa.Text(), nullable=True))
        batch.create_check_constraint(
            "ck_project_lifecycle_events_archive_reason",
            "archive_reason IS NULL OR archive_reason IN "
            "('completed', 'superseded', 'cancelled', 'test_development', 'other')",
        )


def downgrade() -> None:
    with op.batch_alter_table("project_lifecycle_events") as batch:
        batch.drop_constraint(
            "ck_project_lifecycle_events_archive_reason",
            type_="check",
        )
        batch.drop_column("archive_reason_note")
        batch.drop_column("archive_reason")
    with op.batch_alter_table("projects") as batch:
        batch.drop_constraint("ck_projects_archive_reason", type_="check")
        batch.drop_column("archive_reason_note")
        batch.drop_column("archive_reason")
