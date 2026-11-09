"""Exercise one disposable authenticated Telaryn workflow against PostgreSQL.

This module is intentionally invoked only by the container CI job after a fresh
database migration. It creates an isolated temporary user and workspace, then
uses the public API to prove local authentication, workspace ownership, UTC
timestamps, and one atomic drawer commit work with PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user import User
from app.models.project import Project
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password


def require(condition: bool, message: str) -> None:
    """Raise a focused failure so the CI log identifies the broken contract."""
    if not condition:
        raise RuntimeError(message)


def create_verification_identity(password: str) -> str:
    """Create an isolated user without changing the configured local owner."""
    token = secrets.token_hex(8)
    email = f"postgres-verification-{token}@example.com"
    with SessionLocal() as db:
        user = User(
            email=email,
            display_name="PostgreSQL verification",
            password_hash=hash_password(password),
        )
        db.add(user)
        db.flush()

        workspace = Workspace(
            name=f"PostgreSQL verification {token}",
            created_by_user_id=user.id,
        )
        db.add(workspace)
        db.flush()
        db.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role="owner",
            )
        )
        db.commit()
        require(
            db.scalar(select(User).where(User.email == email)) is not None,
            "PostgreSQL verification user was not persisted.",
        )
    return email


def create_foreign_project() -> int:
    """Create a second workspace target used only to prove isolation."""
    token = secrets.token_hex(8)
    with SessionLocal() as db:
        user = User(
            email=f"postgres-isolation-{token}@example.com",
            display_name="PostgreSQL isolation verification",
            password_hash=hash_password(secrets.token_urlsafe(24)),
        )
        db.add(user)
        db.flush()
        workspace = Workspace(
            name=f"PostgreSQL isolation {token}",
            created_by_user_id=user.id,
        )
        db.add(workspace)
        db.flush()
        db.add(
            WorkspaceMembership(
                workspace_id=workspace.id,
                user_id=user.id,
                role="owner",
            )
        )
        project = Project(workspace_id=workspace.id, name="Foreign verification")
        db.add(project)
        db.commit()
        return project.id


def require_utc(value: str, label: str) -> None:
    """Confirm API timestamps remain explicit UTC instants."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, f"{label} is missing timezone information.")
    require(
        parsed.utcoffset() == timedelta(0),
        f"{label} is not UTC.",
    )


def main() -> None:
    """Run the authenticated PostgreSQL integration proof for container CI."""
    require(engine.dialect.name == "postgresql", "Verification must use PostgreSQL.")

    password = secrets.token_urlsafe(24)
    email = create_verification_identity(password)
    foreign_project_id = create_foreign_project()
    origin = settings.frontend_origins.split(",", maxsplit=1)[0].strip()
    headers = {"Origin": origin}
    suffix = secrets.token_hex(4)

    # HTTPS keeps the proof valid when staging marks its session cookie Secure.
    with TestClient(app, base_url="https://telaryn-verification.invalid") as client:
        login = client.post(
            "/auth/login",
            headers=headers,
            json={"email": email, "password": password},
        )
        require(login.status_code == 200, f"Login failed: {login.status_code}")
        require(login.json()["email"] == email, "Login returned the wrong identity.")

        foreign_project = client.get(f"/projects/{foreign_project_id}", headers=headers)
        require(
            foreign_project.status_code == 404,
            "Authenticated recovery verification crossed the workspace boundary.",
        )

        project = client.post(
            "/projects/",
            headers=headers,
            json={"name": f"PostgreSQL verification {suffix}"},
        )
        require(project.status_code == 201, f"Project creation failed: {project.status_code}")
        project_id = project.json()["id"]
        require_utc(project.json()["created_at"], "Project created_at")

        ticket = client.post(
            "/tickets/",
            headers=headers,
            json={
                "title": "Verify PostgreSQL drawer commit",
                "description": "Created only by the disposable integration proof.",
                "project_id": project_id,
                "acceptance_criteria": [{"text": "Commit through the drawer"}],
                "subtasks": [{"title": "Verify activity evidence"}],
            },
        )
        require(ticket.status_code == 201, f"Ticket creation failed: {ticket.status_code}")
        ticket_data = ticket.json()
        require_utc(ticket_data["created_at"], "Ticket created_at")

        committed = client.put(
            f"/tickets/{ticket_data['id']}/drawer-session",
            headers=headers,
            json={
                "ticket": {
                    "title": "Verify PostgreSQL drawer commit",
                    "description": "Committed as one reviewed PostgreSQL transaction.",
                    "priority": "medium",
                    "ticket_type": "task",
                    "status": "ready",
                    "project_id": project_id,
                },
                "acceptance_criteria": [
                    {"text": "Commit through the drawer", "completed": True}
                ],
                "subtasks": [
                    {"title": "Verify activity evidence", "status": "done"}
                ],
                "note": "PostgreSQL drawer verification completed.",
            },
        )
        require(
            committed.status_code == 200,
            f"Drawer commit failed: {committed.status_code}",
        )
        result = committed.json()
        require(
            result["acceptance_criteria"][0]["completed"] is True,
            "Drawer criterion completion was not persisted.",
        )
        require(
            result["subtasks"][0]["status"] == "done",
            "Drawer subtask completion was not persisted.",
        )

        activity = client.get(
            f"/tickets/{ticket_data['id']}/activity-events",
            headers=headers,
        )
        require(activity.status_code == 200, f"Activity lookup failed: {activity.status_code}")
        drawer_events = [
            event
            for event in activity.json()
            if event["event_type"] == "drawer_session_committed"
        ]
        require(len(drawer_events) == 1, "Drawer commit did not produce one activity event.")
        require_utc(drawer_events[0]["created_at"], "Drawer activity created_at")


if __name__ == "__main__":
    main()
