"""Verify deployment-safe configuration aliases without changing local defaults."""

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from app.core.config import Settings
from app.schemas.auth import LoginRequest


def test_frontend_origins_accepts_atlas_environment_alias(monkeypatch):
    monkeypatch.setenv("ATLAS_FRONTEND_ORIGINS", "http://localhost:8080")

    settings = Settings(_env_file=None)

    assert settings.frontend_origins == "http://localhost:8080"


def test_default_bootstrap_email_can_be_used_for_login():
    settings = Settings(_env_file=None)

    assert LoginRequest(email=settings.bootstrap_user_email, password="long-enough-password").email


def test_feedback_reviewer_ids_default_empty_and_accept_positive_json_ids(monkeypatch):
    monkeypatch.delenv("ATLAS_FEEDBACK_REVIEWER_IDS", raising=False)
    assert Settings(_env_file=None).feedback_reviewer_ids == []

    monkeypatch.setenv("ATLAS_FEEDBACK_REVIEWER_IDS", "[2,17]")
    assert Settings(_env_file=None).feedback_reviewer_ids == [2, 17]


@pytest.mark.parametrize("value", ["not-json", "[0]", "[-1]", "[\"invalid\"]"])
def test_invalid_feedback_reviewer_configuration_fails_closed(monkeypatch, value):
    monkeypatch.setenv("ATLAS_FEEDBACK_REVIEWER_IDS", value)
    with pytest.raises((ValidationError, SettingsError)):
        Settings(_env_file=None)
