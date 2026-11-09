"""Verify the preference upgrade preserves memberships and supports rollback."""

from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_default_project_upgrade_and_downgrade(tmp_path):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    url = f"sqlite:///{tmp_path / 'defaults.db'}"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "e1b2c3d4f5a6")
    engine = create_engine(url)
    with engine.connect() as connection:
        before = connection.execute(text("SELECT id, user_id, workspace_id FROM workspace_memberships")).all()
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id, user_id, workspace_id FROM workspace_memberships")).all() == before
        assert connection.execute(text("SELECT default_project_id FROM workspace_memberships")).scalars().all() == [None] * len(before)
    command.downgrade(config, "e1b2c3d4f5a6")
    assert "default_project_id" not in {col["name"] for col in inspect(engine).get_columns("workspace_memberships")}
    command.upgrade(config, "head")
    engine.dispose()
