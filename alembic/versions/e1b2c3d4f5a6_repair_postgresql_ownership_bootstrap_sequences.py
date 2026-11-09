"""repair PostgreSQL ownership bootstrap sequences

Revision ID: e1b2c3d4f5a6
Revises: c6f1a4d9e205
Create Date: 2026-09-02

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "e1b2c3d4f5a6"
down_revision: Union[str, Sequence[str], None] = "c6f1a4d9e205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Advance PostgreSQL identity sequences past the fixed bootstrap records."""
    if op.get_bind().dialect.name != "postgresql":
        return

    for table_name in ("users", "workspaces"):
        op.execute(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
        )


def downgrade() -> None:
    """Keep sequence repair forward-only because it does not alter user data."""
