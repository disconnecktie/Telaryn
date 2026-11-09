"""Verify liveness and migration-aware readiness behavior."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_liveness_does_not_depend_on_database_state() -> None:
    assert client.get("/health").json() == {"status": "healthy"}


def test_readiness_requires_current_database_revision() -> None:
    with patch("app.main.database_migration_state", return_value="current"):
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_hides_database_failure_details() -> None:
    with patch("app.main.database_migration_state", return_value="unavailable"):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
