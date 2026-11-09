"""Verify private deployment helpers expose only deliberately requested identity data."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register complete metadata
from app import cli
from app.db.base import Base
from app.models.user import User


@pytest.fixture
def cli_database(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(cli, "SessionLocal", lambda: Session(engine))
    try:
        yield engine
    finally:
        engine.dispose()


def test_show_user_id_normalizes_exact_email_and_prints_only_id(capsys, cli_database):
    with Session(cli_database) as db:
        user = User(email="admin@example.test", display_name="Private Name", password_hash="hash")
        db.add(user)
        db.commit()
        expected_id = user.id

    cli.show_user_id(" ADMIN@EXAMPLE.TEST ")

    output = capsys.readouterr().out.strip()
    assert output == f"TELARYN_USER_ID={expected_id}"
    assert "admin@example.test" not in output
    assert "Private Name" not in output


def test_show_user_id_fails_without_enumerating_users(cli_database):
    with pytest.raises(SystemExit, match="No Telaryn user exists with that email"):
        cli.show_user_id("missing@example.test")
