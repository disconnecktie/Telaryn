"""Verify bounded intake data and reversible storage without enabling collection."""

from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.models.access_request import AccessRequest
from app.schemas.access_request import AccessRequestCreate, AccessRequestReview
from app.services.access_requests import build_access_request


def payload(**overrides):
    return {"first_name": "  Example  ", "last_name": "Visitor", "email": "visitor@example.com", "referral_source": "github", **overrides}


@pytest.mark.parametrize("changes", [
    {"first_name": " "}, {"last_name": "x" * 101}, {"email": "invalid"},
    {"phone": "1" * 41}, {"biography": "x" * 1001},
    {"notes": "x" * 1001}, {"referral_detail": "x" * 201},
    {"referral_source": "unknown"}, {"status": "approved"},
    {"workspace_id": 1}, {"user_id": 1},
])
def test_invalid_or_privileged_input_rejected(changes):
    with pytest.raises(ValidationError):
        AccessRequestCreate(**payload(**changes))


def test_retention_and_minimal_data():
    request = build_access_request(AccessRequestCreate(**payload()))
    assert request.first_name == "Example"
    assert request.status == "new"
    assert request.phone == request.biography == request.notes == ""
    assert request.expires_at - request.created_at == timedelta(days=90)
    assert request.updated_at == request.created_at
    assert not inspect(AccessRequest).relationships
    assert not any(column.foreign_keys for column in AccessRequest.__table__.columns)


def test_review_status_allowlist():
    for status in ["new", "reviewed", "approved", "declined", "closed"]:
        assert AccessRequestReview(status=status).status == status
    with pytest.raises(ValidationError):
        AccessRequestReview(status="provisioned")


def test_migration_preserves_accounts_and_round_trips(tmp_path):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    url = f"sqlite:///{tmp_path / 'intake.db'}"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "f3c79a04b201")
    engine = create_engine(url)
    with engine.connect() as conn:
        before = conn.execute(text("SELECT id, email FROM users")).all()
    command.upgrade(config, "head")
    with Session(engine) as db:
        db.add(build_access_request(AccessRequestCreate(**payload())))
        db.commit()
        record = db.scalar(select(AccessRequest))
        assert record.first_name == "Example"
        assert record.expires_at - record.created_at == timedelta(days=90)
    command.downgrade(config, "f3c79a04b201")
    assert "access_requests" not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id, email FROM users")).all() == before
    command.upgrade(config, "head")
    assert "access_requests" in inspect(engine).get_table_names()
    engine.dispose()
