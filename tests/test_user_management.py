"""Exercise deployment-admin lifecycle boundaries without exposing work content."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register complete metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password


ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "correct horse battery staple"


def setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    admin = User(email="admin@example.com", display_name="Admin", password_hash=hash_password(PASSWORD))
    member = User(email="member@example.com", display_name="Member", password_hash=hash_password(PASSWORD))
    db.add_all([admin, member])
    db.flush()
    workspace = Workspace(name="Private workspace", created_by_user_id=admin.id)
    db.add(workspace)
    db.flush()
    db.add_all([
        WorkspaceMembership(workspace_id=workspace.id, user_id=admin.id, role="owner"),
        WorkspaceMembership(workspace_id=workspace.id, user_id=member.id, role="owner"),
    ])
    db.commit()
    monkeypatch.setattr(settings, "deployment_administrator_ids", [admin.id])

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    return engine, db, admin, member, TestClient(app), TestClient(app)


def teardown(engine, db):
    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()


def login(client, email):
    response = client.post("/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def test_lifecycle_is_deployment_admin_only_and_rejects_disabled_sessions(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        assert member_client.get("/user-management/users").status_code == 403
        listed = admin_client.get("/user-management/users?status=all")
        assert listed.status_code == 200
        item = next(item for item in listed.json()["items"] if item["id"] == member.id)
        assert set(item) == {"id", "email", "display_name", "account_status", "created_at", "disabled_at", "workspace_count"}

        disabled = admin_client.post(f"/user-management/users/{member.id}/disable", headers=ORIGIN, json={"confirmed": True})
        assert disabled.status_code == 200
        assert disabled.json()["account_status"] == "disabled"
        assert member_client.get("/auth/session").status_code == 401
        assert admin_client.post("/auth/login", headers=ORIGIN, json={"email": member.email, "password": PASSWORD}).status_code == 401
        assert db.query(AuthSession).filter_by(user_id=member.id).filter(AuthSession.revoked_at.isnot(None)).count() == 1

        restored = admin_client.post(f"/user-management/users/{member.id}/reactivate", headers=ORIGIN, json={"confirmed": True})
        assert restored.status_code == 200
        assert restored.json()["account_status"] == "active"
        assert member_client.get("/auth/session").status_code == 401
        assert admin_client.post("/auth/login", headers=ORIGIN, json={"email": member.email, "password": PASSWORD}).status_code == 200
    finally:
        teardown(engine, db)


def test_cannot_disable_self_or_last_active_workspace_owner(monkeypatch):
    engine, db, admin, member, admin_client, _ = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        own = admin_client.post(f"/user-management/users/{admin.id}/disable", headers=ORIGIN, json={"confirmed": True})
        assert own.status_code == 409

        db.query(WorkspaceMembership).filter_by(user_id=member.id).delete()
        db.commit()
        last_owner = admin_client.post(f"/user-management/users/{member.id}/disable", headers=ORIGIN, json={"confirmed": True})
        # The member no longer owns a workspace, so this succeeds.
        assert last_owner.status_code == 200

        second = User(email="second@example.com", display_name="Second", password_hash=hash_password(PASSWORD))
        db.add(second)
        db.flush()
        solo = Workspace(name="Solo", created_by_user_id=second.id)
        db.add(solo)
        db.flush()
        db.add(WorkspaceMembership(workspace_id=solo.id, user_id=second.id, role="owner"))
        db.commit()
        blocked = admin_client.post(f"/user-management/users/{second.id}/disable", headers=ORIGIN, json={"confirmed": True})
        assert blocked.status_code == 409
    finally:
        teardown(engine, db)


def test_revoke_all_sessions_preserves_active_account(monkeypatch):
    engine, db, admin, member, admin_client, member_client = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        login(member_client, member.email)
        response = admin_client.post(f"/user-management/users/{member.id}/revoke-sessions", headers=ORIGIN, json={"confirmed": True})
        assert response.status_code == 200
        assert response.json()["account_status"] == "active"
        assert response.json()["active_session_count"] == 0
        assert member_client.get("/auth/session").status_code == 401
        login(member_client, member.email)
    finally:
        teardown(engine, db)


def test_workspace_membership_management_preserves_active_owner(monkeypatch):
    engine, db, admin, member, admin_client, _ = setup(monkeypatch)
    try:
        login(admin_client, admin.email)
        workspace = db.query(Workspace).one()
        changed = admin_client.patch(
            f"/user-management/users/{member.id}/workspaces/{workspace.id}",
            headers=ORIGIN,
            json={"confirmed": True, "role": "member"},
        )
        assert changed.status_code == 200
        assert changed.json()["workspaces"] == [{"id": workspace.id, "name": workspace.name, "role": "member"}]
        removed = admin_client.request(
            "DELETE",
            f"/user-management/users/{member.id}/workspaces/{workspace.id}",
            headers=ORIGIN,
            json={"confirmed": True},
        )
        assert removed.status_code == 200
        assert removed.json()["workspaces"] == []

        solo = User(email="solo@example.com", display_name="Solo", password_hash=hash_password(PASSWORD))
        db.add(solo)
        db.flush()
        solo_workspace = Workspace(name="Solo workspace", created_by_user_id=solo.id)
        db.add(solo_workspace)
        db.flush()
        db.add(WorkspaceMembership(workspace_id=solo_workspace.id, user_id=solo.id, role="owner"))
        db.commit()
        rejected = admin_client.request(
            "DELETE",
            f"/user-management/users/{solo.id}/workspaces/{solo_workspace.id}",
            headers=ORIGIN,
            json={"confirmed": True},
        )
        assert rejected.status_code == 409
    finally:
        teardown(engine, db)
