"""Exercise the workspace migration against representative pre-auth Telaryn data."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
PRE_WORKSPACE_REVISION = "7a1c4e9d2b60"


class WorkspaceMigrationTests(unittest.TestCase):
    """Protect existing single-user data while the app becomes workspace-aware."""

    def _config_for(self, database_path: Path) -> Config:
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
        return config

    def test_legacy_records_are_adopted_by_only_the_bootstrap_workspace(self) -> None:
        """Upgrade a populated pre-Slice-1 database without rewriting its work IDs."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "legacy-atlas.db"
            config = self._config_for(database_path)
            command.upgrade(config, PRE_WORKSPACE_REVISION)

            engine = create_engine(f"sqlite:///{database_path}")
            timestamp = datetime(2026, 8, 25, 12, 0)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO projects (id, name, description, created_at, updated_at) "
                        "VALUES (41, 'Existing project', 'Keep this', :created_at, :updated_at)"
                    ),
                    {"created_at": timestamp, "updated_at": timestamp},
                )
                connection.execute(
                    text(
                        "INSERT INTO tickets "
                        "(id, project_id, title, description, status, priority, ticket_type, created_at, updated_at) "
                        "VALUES (72, 41, 'Existing ticket', 'Keep this too', 'READY', 'MEDIUM', 'TASK', :created_at, :updated_at)"
                    ),
                    {"created_at": timestamp, "updated_at": timestamp},
                )

            environment = {
                "ATLAS_BOOTSTRAP_USER_EMAIL": "jay@example.test",
                "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME": "Jay",
                "ATLAS_BOOTSTRAP_WORKSPACE_NAME": "Jay's Workspace",
            }
            with patch.dict(os.environ, environment, clear=False):
                command.upgrade(config, "head")

            with engine.connect() as connection:
                user = connection.execute(
                    text("SELECT id, email, display_name FROM users")
                ).one()
                workspace = connection.execute(
                    text("SELECT id, name, created_by_user_id FROM workspaces")
                ).one()
                membership = connection.execute(
                    text("SELECT workspace_id, user_id, role FROM workspace_memberships")
                ).one()
                project = connection.execute(
                    text("SELECT id, workspace_id FROM projects WHERE id = 41")
                ).one()
                ticket = connection.execute(
                    text("SELECT id, project_id, workspace_id FROM tickets WHERE id = 72")
                ).one()

            # Windows will not remove the temporary SQLite file while the
            # engine's pooled DBAPI connection still owns a file handle.
            engine.dispose()

            self.assertEqual(user, (1, "jay@example.test", "Jay"))
            self.assertEqual(workspace, (1, "Jay's Workspace", 1))
            self.assertEqual(membership, (1, 1, "owner"))
            self.assertEqual(project, (41, 1))
            self.assertEqual(ticket, (72, 41, 1))

    def test_fresh_production_placeholder_owner_is_repaired_safely(self) -> None:
        """Repair the exact empty-production bootstrap mistake without changing IDs."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "production-bootstrap.db"
            config = self._config_for(database_path)

            with patch.dict(os.environ, {}, clear=False):
                for variable in (
                    "ENVIRONMENT",
                    "ATLAS_BOOTSTRAP_USER_EMAIL",
                    "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME",
                    "ATLAS_BOOTSTRAP_WORKSPACE_NAME",
                    "ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED",
                ):
                    os.environ.pop(variable, None)
                command.upgrade(config, "a107b010c001")

            environment = {
                "ENVIRONMENT": "production",
                "ATLAS_BOOTSTRAP_USER_EMAIL": "owner@example.test",
                "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME": "Release Administrator",
                "ATLAS_BOOTSTRAP_WORKSPACE_NAME": "Release Administration",
                "ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED": "yes",
            }
            with patch.dict(os.environ, environment, clear=False):
                command.upgrade(config, "head")

            engine = create_engine(f"sqlite:///{database_path}")
            with engine.connect() as connection:
                user = connection.execute(
                    text("SELECT id, email, display_name, password_hash FROM users")
                ).one()
                workspace = connection.execute(
                    text("SELECT id, name, created_by_user_id FROM workspaces")
                ).one()
                membership = connection.execute(
                    text("SELECT workspace_id, user_id, role FROM workspace_memberships")
                ).one()
            engine.dispose()

            self.assertEqual(
                user,
                (1, "owner@example.test", "Release Administrator", None),
            )
            self.assertEqual(workspace, (1, "Release Administration", 1))
            self.assertEqual(membership, (1, 1, "owner"))

    def test_production_repair_requires_explicit_approval(self) -> None:
        """Fail closed when a placeholder exists but the operator has not opted in."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "unapproved-repair.db"
            config = self._config_for(database_path)
            with patch.dict(os.environ, {}, clear=False):
                for variable in (
                    "ENVIRONMENT",
                    "ATLAS_BOOTSTRAP_USER_EMAIL",
                    "ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED",
                ):
                    os.environ.pop(variable, None)
                command.upgrade(config, "a107b010c001")

            with patch.dict(
                os.environ,
                {
                    "ENVIRONMENT": "production",
                    "ATLAS_BOOTSTRAP_USER_EMAIL": "owner@example.test",
                },
                clear=False,
            ):
                os.environ.pop("ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED", None)
                with self.assertRaisesRegex(RuntimeError, "explicit"):
                    command.upgrade(config, "a108b010c002")

            engine = create_engine(f"sqlite:///{database_path}")
            with engine.connect() as connection:
                user = connection.execute(text("SELECT email FROM users")).scalar_one()
            engine.dispose()
            self.assertEqual(user, "atlas.local@example.com")

    def test_production_owner_already_correct_needs_no_repair_approval(self) -> None:
        """No-op when the deployment already bootstrapped its configured owner."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "correct-owner.db"
            config = self._config_for(database_path)
            environment = {
                "ENVIRONMENT": "production",
                "ATLAS_BOOTSTRAP_USER_EMAIL": "owner@example.test",
                "ATLAS_BOOTSTRAP_USER_DISPLAY_NAME": "Release Administrator",
            }
            with patch.dict(os.environ, environment, clear=False):
                os.environ.pop("ATLAS_BOOTSTRAP_OWNER_REPAIR_APPROVED", None)
                command.upgrade(config, "a108b010c002")

            engine = create_engine(f"sqlite:///{database_path}")
            with engine.connect() as connection:
                user = connection.execute(text("SELECT email FROM users")).scalar_one()
            engine.dispose()
            self.assertEqual(user, "owner@example.test")
