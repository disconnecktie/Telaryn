"""add activity actor attribution

Revision ID: 6d3b9a2f8c10
Revises: 2f8a1c6d4e90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d3b9a2f8c10"
down_revision: Union[str, Sequence[str], None] = "2f8a1c6d4e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable ownership preserves honest legacy attribution for pre-auth records.
    with op.batch_alter_table("ticket_status_events") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_ticket_status_events_actor_user_id", ["actor_user_id"])
        batch_op.create_foreign_key(
            "fk_ticket_status_events_actor_user_id_users",
            "users",
            ["actor_user_id"],
            ["id"],
        )
    with op.batch_alter_table("ticket_update_entries") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_ticket_update_entries_actor_user_id", ["actor_user_id"])
        batch_op.create_foreign_key(
            "fk_ticket_update_entries_actor_user_id_users",
            "users",
            ["actor_user_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("ticket_update_entries") as batch_op:
        batch_op.drop_constraint("fk_ticket_update_entries_actor_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_ticket_update_entries_actor_user_id")
        batch_op.drop_column("actor_user_id")
    with op.batch_alter_table("ticket_status_events") as batch_op:
        batch_op.drop_constraint("fk_ticket_status_events_actor_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_ticket_status_events_actor_user_id")
        batch_op.drop_column("actor_user_id")
