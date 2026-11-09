"""Verify intake reviewer isolation, non-provisioning decisions, and retention cleanup."""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.time import utc_now
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.access_request import AccessRequest, AccessRequestEvent, AccessRequestLimit
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent
from app.schemas.access_request import AccessRequestCreate
from app.services.access_requests import build_access_request, purge_expired_requests
from app.services.auth import create_auth_session
from app.services.invitation_delivery import DeliveryResult, InvitationDeliveryUnavailable

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.fixture
def intake(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="reviewer@example.com", display_name="Reviewer")
        db.add(user)
        db.flush()
        workspace = Workspace(name="Private", created_by_user_id=user.id)
        db.add(workspace)
        db.flush()
        db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
        _, token = create_auth_session(db, user)
        record = build_access_request(AccessRequestCreate(first_name="New", last_name="Visitor", email="new@example.com", referral_source="github"))
        db.add(record)
        db.commit()
        monkeypatch.setattr(settings, "access_request_reviewer_ids", [])
        monkeypatch.setattr(settings, "access_request_intake_enabled", False)
        def override():
            yield db
        app.dependency_overrides[get_db] = override
        with TestClient(app) as client:
            yield db, client, user, token, record
        app.dependency_overrides.pop(get_db, None)
    engine.dispose()


def test_review_boundary_and_no_public_submission(intake, monkeypatch):
    db, client, user, token, record = intake
    for path in ["/access-requests/", f"/access-requests/{record.id}"]:
        assert client.get(path).status_code == 401
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/access-requests/").status_code == 403  # even workspace owner
    assert client.get("/access-requests/reviewer-access").json() == {"allowed": False, "new_count": 0}
    assert client.get(f"/access-requests/{record.id}").status_code == 403
    assert client.patch(f"/access-requests/{record.id}", json={"status": "approved"}, headers=ORIGIN).status_code == 403
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [user.id])
    result = client.get("/access-requests/")
    assert result.status_code == 200
    assert client.get("/access-requests/reviewer-access").json() == {"allowed": True, "new_count": 1}
    assert result.headers["cache-control"] == "no-store"
    assert "email" not in result.json()[0]
    assert client.get(f"/access-requests/{record.id}").json()["email"] == "new@example.com"
    assert client.get("/access-requests/?limit=101").status_code == 422
    assert client.get(f"/access-requests/?after_id={record.id}").json() == []
    assert client.post("/access-requests/", headers=ORIGIN, json={}).status_code == 503


def test_lifecycle_is_atomic_idempotent_and_does_not_provision(intake, monkeypatch):
    db, client, user, token, record = intake
    client.cookies.set(settings.session_cookie_name, token)
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [user.id])
    deadline = record.expires_at
    path = f"/access-requests/{record.id}"
    assert client.patch(path, json={"status": "approved"}).status_code == 403
    assert client.patch(path, json={"status": "invalid"}, headers=ORIGIN).status_code == 422
    for status in ["reviewed", "approved", "declined", "closed"]:
        assert client.patch(path, json={"status": status}, headers=ORIGIN).json()["status"] == status
    assert client.patch(path, json={"status": "closed"}, headers=ORIGIN).status_code == 200
    assert db.scalar(select(func.count()).select_from(AccessRequestEvent)) == 4
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(WorkspaceMembership)) == 1
    assert record.expires_at == deadline
    assert len(client.get(path).json()["history"]) == 4
    assert client.get("/access-requests/reviewer-access").json()["new_count"] == 0


def test_expiry_hides_records_and_purges_history(intake, monkeypatch):
    db, client, user, token, record = intake
    client.cookies.set(settings.session_cookie_name, token)
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [user.id])
    client.patch(f"/access-requests/{record.id}", json={"status": "reviewed"}, headers=ORIGIN)
    now = utc_now()
    record.expires_at = now - timedelta(seconds=1)
    live = build_access_request(AccessRequestCreate(first_name="Live", last_name="Visitor", email="live@example.com", referral_source="other"))
    db.add(live)
    db.commit()
    assert client.get(f"/access-requests/{record.id}").status_code == 404
    assert client.patch(f"/access-requests/{record.id}", json={"status": "approved"}, headers=ORIGIN).status_code == 404
    assert [r["id"] for r in client.get("/access-requests/").json()] == [live.id]
    assert client.get("/access-requests/reviewer-access").json()["new_count"] == 1
    assert purge_expired_requests(db, now=now) == 1
    db.commit()
    assert db.scalar(select(func.count()).select_from(AccessRequestEvent)) == 0
    assert db.scalar(select(func.count()).select_from(AccessRequest)) == 1
    assert purge_expired_requests(db, now=now) == 0


def test_public_submission_non_disclosure_limits_and_validation(intake, monkeypatch):
    db, client, user, token, record = intake
    assert client.get("/access-requests/availability").json() == {"enabled": False}
    monkeypatch.setattr(settings, "access_request_intake_enabled", True)
    assert client.get("/access-requests/availability").json() == {"enabled": False}
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [user.id])
    db.add(AccessRequestLimit(id=1, window_start=utc_now(), accepted=0))
    db.commit()
    assert client.get("/access-requests/availability").json() == {"enabled": True}
    payload = dict(first_name="Visitor", last_name="Example", email="unknown@example.com", referral_source="github")
    assert client.post("/access-requests/", json=payload).status_code == 403
    invalid = client.post("/access-requests/", headers=ORIGIN, json={**payload, "email": "private-invalid-data"})
    assert invalid.status_code == 422
    assert "private-invalid-data" not in invalid.text
    assert client.post("/access-requests/", headers=ORIGIN, json={**payload, "status": "approved"}).status_code == 422
    assert client.post("/access-requests/", headers={**ORIGIN, "Content-Type": "application/json"}, content="x" * 17000).status_code == 413
    first = client.post("/access-requests/", headers=ORIGIN, json=payload)
    second = client.post("/access-requests/", headers=ORIGIN, json={**payload, "email": user.email})
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert first.headers["cache-control"] == "no-store"
    assert db.scalar(select(func.count()).select_from(User)) == 1
    assert db.scalar(select(func.count()).select_from(WorkspaceMembership)) == 1
    counter = db.get(AccessRequestLimit, 1)
    counter.accepted = 30
    db.commit()
    assert client.post("/access-requests/", headers=ORIGIN, json=payload).status_code == 429
    counter.window_start = utc_now() - timedelta(hours=2)
    db.commit()
    assert client.post("/access-requests/", headers=ORIGIN, json=payload).status_code == 202


def test_queue_filters_pagination_and_authorization(intake, monkeypatch):
    db, client, user, token, record = intake
    assert client.post("/access-requests/queue", headers=ORIGIN, json={}).status_code == 401
    client.cookies.set(settings.session_cookie_name, token)
    assert client.post("/access-requests/queue", headers=ORIGIN, json={}).status_code == 403
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [user.id])
    for index in range(22):
        row = build_access_request(AccessRequestCreate(first_name="Queue", last_name=str(index), email=f"q{index}@example.com", referral_source="github"))
        db.add(row)
    record.status = "reviewed"
    db.commit()
    def queue(**query):
        response = client.post("/access-requests/queue", headers=ORIGIN, json=query)
        assert response.status_code == 200
        return response.json()
    first = queue()
    second = queue(page=2)
    assert first["total"] == 22 and len(first["items"]) == 20
    assert second["pages"] == 2 and len(second["items"]) == 2
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    assert queue(status="reviewed")["total"] == 1
    assert queue(status=None)["items"][0]["status"] == "new"
    assert queue(search="Q1@EXAMPLE.COM")["total"] == 1
    assert queue(search="%")["total"] == 0
    assert queue(page=999)["page"] == 2


def test_invitation_api_requires_review_and_owner_then_activates_once(intake, monkeypatch):
    db, client, owner, owner_token, record = intake
    client.cookies.set(settings.session_cookie_name, owner_token)
    path = f"/access-requests/{record.id}/invitation"
    assert client.post(path, headers=ORIGIN, json={}).status_code == 403
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [owner.id])
    workspace = db.scalar(select(Workspace).where(Workspace.created_by_user_id == owner.id))
    assert client.patch(f"/access-requests/{record.id}", headers=ORIGIN,
                        json={"status": "approved"}).status_code == 200
    issued = client.post(path, headers=ORIGIN, json={})
    assert issued.status_code == 200
    assert issued.json()["delivery"] == "manual"
    assert "token=" in issued.json()["activation_link"]
    assert "token_hash" not in issued.text
    token = parse_qs(urlparse(issued.json()["activation_link"]).fragment.split("?", 1)[1])["token"][0]
    assert client.post("/access-requests/invitations/inspect", json={"token": token}).status_code == 403
    inspection = client.post("/access-requests/invitations/inspect", headers=ORIGIN,
                             json={"token": token})
    assert inspection.json()["workspace_name"] == "Your private workspace"
    assert inspection.json()["account_email"] == "new@example.com"
    assert inspection.json()["requires_sign_in"] is False
    activated = client.post("/access-requests/invitations/accept-new", headers=ORIGIN, json={
        "token": token, "password": "correct horse battery staple",
        "password_confirmation": "correct horse battery staple",
    })
    assert activated.status_code == 201
    assert "email" not in activated.text
    assert client.post("/access-requests/invitations/accept-new", headers=ORIGIN, json={
        "token": token, "password": "correct horse battery staple",
        "password_confirmation": "correct horse battery staple",
    }).status_code == 409
    invited = db.scalar(select(User).where(User.email == "new@example.com"))
    assert invited is not None
    assert db.scalar(select(func.count()).select_from(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id != workspace.id,
        WorkspaceMembership.user_id == invited.id,
    )) == 1
    personal = db.scalar(select(Workspace).where(Workspace.created_by_user_id == invited.id))
    assert personal.name == "New's Workspace"
    invitation = db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.request_id == record.id))
    assert invitation.status == "accepted" and invitation.token_hash is None


def test_azure_delivery_returns_no_bearer_link_and_records_outcome(intake, monkeypatch):
    db, client, owner, owner_token, record = intake
    client.cookies.set(settings.session_cookie_name, owner_token)
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [owner.id])
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "invitation_delivery_provider", "azure")
    client.patch(f"/access-requests/{record.id}", headers=ORIGIN, json={"status": "approved"})
    captured = {}

    def fake_delivery(**values):
        captured.update(values)
        return DeliveryResult(provider="azure", message_id="message-123"), None

    monkeypatch.setattr("app.api.access_requests.deliver_invitation", fake_delivery)
    response = client.post(f"/access-requests/{record.id}/invitation", headers=ORIGIN, json={})
    assert response.status_code == 200
    assert response.json()["delivery"] == "azure"
    assert "activation_link" not in response.json()
    assert "token=" not in response.text
    assert captured["recipient_email"] == "new@example.com"
    invitation = db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.request_id == record.id))
    assert invitation.status == "pending"
    assert invitation.delivery_provider == "azure"
    assert invitation.delivery_message_id == "message-123"
    assert invitation.delivered_at is not None


def test_delivery_failure_invalidates_generation_for_explicit_retry(intake, monkeypatch):
    db, client, owner, owner_token, record = intake
    client.cookies.set(settings.session_cookie_name, owner_token)
    monkeypatch.setattr(settings, "access_request_reviewer_ids", [owner.id])
    client.patch(f"/access-requests/{record.id}", headers=ORIGIN, json={"status": "approved"})

    def fail_delivery(**_values):
        raise InvitationDeliveryUnavailable("provider detail that must not escape")

    monkeypatch.setattr("app.api.access_requests.deliver_invitation", fail_delivery)
    response = client.post(f"/access-requests/{record.id}/invitation", headers=ORIGIN, json={})
    assert response.status_code == 502
    assert "provider detail" not in response.text
    invitation = db.scalar(select(WorkspaceInvitation).where(WorkspaceInvitation.request_id == record.id))
    assert invitation.status == "delivery_failed"
    assert invitation.token_hash is None
    assert invitation.delivery_attempted_at is not None
    events = [event.event for event in db.scalars(select(WorkspaceInvitationEvent).where(
        WorkspaceInvitationEvent.invitation_id == invitation.id
    ).order_by(WorkspaceInvitationEvent.id))]
    assert events == ["issued", "delivery_failed"]
