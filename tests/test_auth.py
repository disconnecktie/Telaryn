"""Verify local credentials, opaque sessions, origin checks, expiry, and logout."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register complete metadata
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.models.project import Project
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password, utcnow


ORIGIN = {"Origin": "http://localhost:5173"}


def build_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(
        email="jay@example.com",
        display_name="Jay",
        password_hash=hash_password("correct horse battery staple"),
    )
    db.add(user)
    db.flush()
    workspace = Workspace(name="Jay's Workspace", created_by_user_id=user.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.commit()

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    return engine, db, TestClient(app)


def close_client(engine, db):
    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()


def test_login_session_and_logout_lifecycle():
    engine, db, client = build_client()
    try:
        login = client.post(
            "/auth/login",
            headers=ORIGIN,
            json={"email": "jay@example.com", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200
        assert login.json()["workspace_name"] == "Jay's Workspace"
        assert "HttpOnly" in login.headers["set-cookie"]
        assert client.get("/auth/session").status_code == 200
        assert client.get("/tickets/").status_code == 200

        logout = client.delete("/auth/session", headers=ORIGIN)
        assert logout.status_code == 204
        assert client.get("/auth/session").status_code == 401
    finally:
        close_client(engine, db)


def test_invalid_credentials_and_origins_do_not_disclose_details():
    engine, db, client = build_client()
    try:
        missing_origin = client.post(
            "/auth/login",
            json={"email": "jay@example.com", "password": "incorrect password"},
        )
        assert missing_origin.status_code == 403
        invalid = client.post(
            "/auth/login",
            headers=ORIGIN,
            json={"email": "nobody@example.com", "password": "incorrect password"},
        )
        assert invalid.status_code == 401
        assert invalid.json()["detail"] == "Invalid email or password."
        assert client.get("/tickets/").status_code == 401
    finally:
        close_client(engine, db)


def test_expired_session_is_rejected():
    engine, db, client = build_client()
    try:
        assert client.post(
            "/auth/login",
            headers=ORIGIN,
            json={"email": "jay@example.com", "password": "correct horse battery staple"},
        ).status_code == 200
        from app.models.auth_session import AuthSession

        session = db.query(AuthSession).one()
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        assert client.get("/auth/session").status_code == 401
    finally:
        close_client(engine, db)


def test_default_project_persists_across_sessions_and_rejects_foreign_projects():
    engine, db, client = build_client()
    try:
        assert client.get("/preferences/").status_code == 401
        credentials = {"email": "jay@example.com", "password": "correct horse battery staple"}
        assert client.post("/auth/login", headers=ORIGIN, json=credentials).status_code == 200
        workspace = db.query(Workspace).one()
        project = Project(name="Default", workspace_id=workspace.id)
        db.add(project)
        db.flush()
        other = Workspace(name="Other", created_by_user_id=workspace.created_by_user_id)
        db.add(other)
        db.flush()
        foreign = Project(name="Private", workspace_id=other.id)
        db.add(foreign)
        db.commit()
        assert client.get("/preferences/").json() == {"default_project_id": None}
        assert client.put("/preferences/", headers=ORIGIN, json={"default_project_id": project.id}).status_code == 200
        second_device = TestClient(app)
        second_device.post("/auth/login", headers=ORIGIN, json=credentials)
        assert second_device.get("/preferences/").json() == {"default_project_id": project.id}
        assert client.put("/preferences/", headers=ORIGIN, json={"default_project_id": foreign.id}).status_code == 404
        assert client.put("/preferences/", headers=ORIGIN, json={"default_project_id": 99999}).status_code == 404
        assert client.put("/preferences/", headers=ORIGIN, json={"default_project_id": True}).status_code == 422
        assert client.put("/preferences/", json={"default_project_id": None}).status_code == 403
        assert second_device.get("/preferences/").json() == {"default_project_id": project.id}
        client.put("/preferences/", headers=ORIGIN, json={"default_project_id": None})
        assert second_device.get("/preferences/").json() == {"default_project_id": None}
        another_user = User(email="other@example.com", display_name="Other", password_hash=hash_password("another secure password"))
        db.add(another_user)
        db.flush()
        db.add(WorkspaceMembership(user_id=another_user.id, workspace_id=workspace.id))
        db.commit()
        client.put("/preferences/", headers=ORIGIN, json={"default_project_id": project.id})
        other_client = TestClient(app)
        other_client.post("/auth/login", headers=ORIGIN, json={"email": "other@example.com", "password": "another secure password"})
        assert other_client.get("/preferences/").json() == {"default_project_id": None}
        membership = db.query(WorkspaceMembership).filter_by(user_id=workspace.created_by_user_id, workspace_id=workspace.id).one()
        membership.default_project_id = foreign.id
        db.commit()
        assert second_device.get("/preferences/").json() == {"default_project_id": None}
    finally:
        close_client(engine, db)
