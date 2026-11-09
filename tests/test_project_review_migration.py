"""Exercise Project Review schema reconciliation against an early applied revision."""

from __future__ import annotations

import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]
BEFORE_PROJECT_REVIEW_REVISION = "b4a6f8c2d190"
EARLY_PROJECT_REVIEW_REVISION = "c7d2e4f8a910"


def config_for(database_path: Path) -> Config:
    """Point Alembic at one isolated SQLite database."""
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    return config


def test_early_project_review_attempt_schema_reconciles_without_data_loss() -> None:
    """Upgrade a stamped development table that predates snapshot-reuse metadata."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_path = Path(temporary_directory) / "early-project-review.db"
        config = config_for(database_path)
        command.upgrade(config, BEFORE_PROJECT_REVIEW_REVISION)

        engine = create_engine(f"sqlite:///{database_path}")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE project_review_attempts (
                        id INTEGER NOT NULL PRIMARY KEY,
                        workspace_id INTEGER NOT NULL,
                        project_id INTEGER NOT NULL,
                        requested_by_user_id INTEGER NOT NULL,
                        snapshot_version VARCHAR(64) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        provider VARCHAR(100) NOT NULL,
                        model VARCHAR(100) NOT NULL,
                        result JSON,
                        safe_error_category VARCHAR(50),
                        duration_ms INTEGER,
                        created_at DATETIME NOT NULL,
                        completed_at DATETIME
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO project_review_attempts (
                        id, workspace_id, project_id, requested_by_user_id,
                        snapshot_version, status, provider, model, created_at
                    ) VALUES (
                        7, 1, 1, 1, 'early-snapshot', 'FAILED',
                        'mock', 'mock-v2', '2026-08-28 08:00:00'
                    )
                    """
                )
            )

        command.stamp(config, EARLY_PROJECT_REVIEW_REVISION)
        command.upgrade(config, "head")

        schema = inspect(engine)
        columns = {
            column["name"]
            for column in schema.get_columns("project_review_attempts")
        }
        indexes = {
            index["name"]
            for index in schema.get_indexes("project_review_attempts")
        }
        with engine.connect() as connection:
            preserved_attempt = connection.execute(
                text(
                    """
                    SELECT id, snapshot_version, status, successful_snapshot_key
                    FROM project_review_attempts
                    WHERE id = 7
                    """
                )
            ).one()

        engine.dispose()

        assert "successful_snapshot_key" in columns
        assert "uq_project_review_success_per_snapshot" not in {
            constraint["name"]
            for constraint in schema.get_unique_constraints(
                "project_review_attempts"
            )
        }
        assert "ix_project_review_success_lookup" in indexes
        assert preserved_attempt == (7, "early-snapshot", "FAILED", None)
