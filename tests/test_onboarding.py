"""Verify onboarding is activity-derived, workspace-scoped, and dismissible."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.my_work_preference import MyWorkPreference
from app.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from app.models.ticket_update_entry import TicketUpdateEntry
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "correct horse battery staple"


def test_onboarding_progress_tracks_approved_work_and_visibility():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = User(email="learner@example.com", display_name="Learner", password_hash=hash_password(PASSWORD))
    db.add(user)
    db.flush()
    workspace = Workspace(name="Learner Workspace", created_by_user_id=user.id)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="owner"))
    db.commit()

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)
    try:
        assert client.post("/auth/login", headers=ORIGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
        response = client.get("/onboarding/")
        assert response.status_code == 200
        assert [item["completed"] for item in response.json()["milestones"]] == [False] * 4
        ticket = Ticket(workspace_id=workspace.id, title="Learn Telaryn", status=TicketStatus.READY, priority=TicketPriority.MEDIUM, ticket_type=TicketType.TASK)
        db.add(ticket)
        db.flush()
        db.add(AcceptanceCriterion(ticket_id=ticket.id, text="The loop is understood", sort_order=0))
        db.add(MyWorkPreference(user_id=user.id, workspace_id=workspace.id, ticket_id=ticket.id, is_current_focus=True))
        db.add(TicketUpdateEntry(ticket_id=ticket.id, actor_user_id=user.id, content="Started the first step."))
        db.commit()
        progress = client.get("/onboarding/").json()
        assert progress["completed"] is True
        assert all(item["completed"] for item in progress["milestones"])
        hidden = client.patch("/onboarding/", headers=ORIGIN, json={"dismissed": True}).json()
        assert hidden["dismissed"] is True
        assert hidden["show_panel"] is False
        reopened = client.patch("/onboarding/", headers=ORIGIN, json={"dismissed": False}).json()
        assert reopened["show_panel"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        engine.dispose()
