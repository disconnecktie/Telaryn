"""Verify deterministic search matching, filters, and workspace isolation."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password


ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "correct horse battery staple"


def build_search_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    owner = User(
        email="search@example.com",
        display_name="Search Owner",
        password_hash=hash_password(PASSWORD),
    )
    outsider = User(
        email="outside@example.com",
        display_name="Outside",
        password_hash=hash_password(PASSWORD),
    )
    db.add_all([owner, outsider])
    db.flush()
    workspace = Workspace(name="Search Workspace", created_by_user_id=owner.id)
    other_workspace = Workspace(name="Other Workspace", created_by_user_id=outsider.id)
    db.add_all([workspace, other_workspace])
    db.flush()
    db.add_all([
        WorkspaceMembership(workspace_id=workspace.id, user_id=owner.id, role="owner"),
        WorkspaceMembership(
            workspace_id=other_workspace.id,
            user_id=outsider.id,
            role="owner",
        ),
    ])
    db.flush()

    project = Project(
        workspace_id=workspace.id,
        name="Telaryn Development",
        description="Build secure cross-project discovery.",
        purpose="Reduce time spent finding authoritative work.",
        why_it_matters="Search must preserve workspace privacy.",
    )
    archived_project = Project(
        workspace_id=workspace.id,
        name="Preserved Migration",
        archived_at=datetime(2026, 9, 14, 8, 0),
    )
    private_project = Project(
        workspace_id=workspace.id,
        name="Private Planning",
        ai_context_enabled=False,
    )
    other_project = Project(
        workspace_id=other_workspace.id,
        name="Forbidden Needle Project",
    )
    db.add_all([project, archived_project, private_project, other_project])
    db.flush()

    ticket = Ticket(
        workspace_id=workspace.id,
        project_id=project.id,
        title="Implement workspace search",
        description="Match tickets without an AI provider.",
        status=TicketStatus.READY,
    )
    completed_ticket = Ticket(
        workspace_id=workspace.id,
        project_id=project.id,
        title="Completed discovery spike",
        status=TicketStatus.DONE,
    )
    archived_ticket = Ticket(
        workspace_id=workspace.id,
        project_id=archived_project.id,
        title="Archived migration notes",
    )
    private_ticket = Ticket(
        workspace_id=workspace.id,
        project_id=private_project.id,
        title="Private but authorized result",
        ai_context_enabled=False,
    )
    other_ticket = Ticket(
        workspace_id=other_workspace.id,
        project_id=other_project.id,
        title="Forbidden Needle Ticket",
    )
    db.add_all([
        ticket,
        completed_ticket,
        archived_ticket,
        private_ticket,
        other_ticket,
    ])
    db.flush()

    criterion = AcceptanceCriterion(
        ticket_id=ticket.id,
        text="Search explains which field matched.",
    )
    completed_criterion = AcceptanceCriterion(
        ticket_id=ticket.id,
        text="Completed criterion match",
        completed=True,
    )
    deferred_criterion = AcceptanceCriterion(
        ticket_id=ticket.id,
        text="Deferred criterion match",
        deferred=True,
    )
    subtask = Subtask(
        ticket_id=ticket.id,
        title="Build deterministic query",
        description="Return bounded grouped results.",
    )
    done_subtask = Subtask(
        ticket_id=ticket.id,
        title="Completed subtask match",
        status=SubtaskStatus.DONE,
    )
    other_criterion = AcceptanceCriterion(
        ticket_id=other_ticket.id,
        text="Forbidden Needle Criterion",
    )
    other_subtask = Subtask(
        ticket_id=other_ticket.id,
        title="Forbidden Needle Subtask",
    )
    db.add_all([
        criterion,
        completed_criterion,
        deferred_criterion,
        subtask,
        done_subtask,
        other_criterion,
        other_subtask,
    ])
    db.commit()

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    client = TestClient(app)
    assert client.post(
        "/auth/login",
        headers=ORIGIN,
        json={"email": owner.email, "password": PASSWORD},
    ).status_code == 200
    return engine, db, client, {
        "project": project,
        "archived_project": archived_project,
        "private_project": private_project,
        "ticket": ticket,
        "criterion": criterion,
        "subtask": subtask,
    }


def close_search_client(engine, db):
    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()


def result_ids(payload):
    return {
        item["id"]
        for group in ("projects", "tickets", "acceptance_criteria", "subtasks")
        for item in payload[group]
    }


def test_searches_project_ticket_and_child_text_with_parent_context():
    engine, db, client, records = build_search_client()
    try:
        project_result = client.get("/search/", params={"q": "authoritative"}).json()
        assert project_result["projects"][0]["id"] == records["project"].id
        assert project_result["projects"][0]["matched_field"] == "Project purpose"

        ticket_result = client.get("/search/", params={"q": "WITHOUT AN AI"}).json()
        assert ticket_result["tickets"][0]["id"] == records["ticket"].id
        assert ticket_result["tickets"][0]["matched_field"] == "Ticket description"

        criterion_result = client.get("/search/", params={"q": "field matched"}).json()
        criterion = criterion_result["acceptance_criteria"][0]
        assert criterion["id"] == records["criterion"].id
        assert criterion["ticket_id"] == records["ticket"].id
        assert criterion["project_name"] == "Telaryn Development"

        subtask_result = client.get("/search/", params={"q": "bounded grouped"}).json()
        subtask = subtask_result["subtasks"][0]
        assert subtask["id"] == records["subtask"].id
        assert subtask["matched_field"] == "Subtask description"
    finally:
        close_search_client(engine, db)


def test_searches_human_and_opaque_references():
    engine, db, client, records = build_search_client()
    try:
        project = client.get(
            "/search/",
            params={"q": f"PRJ-{records['project'].workspace_project_number:03d}"},
        ).json()
        assert project["projects"][0]["id"] == records["project"].id

        ticket = client.get(
            "/search/",
            params={"q": records["ticket"].public_id.lower()},
        ).json()
        assert ticket["tickets"][0]["id"] == records["ticket"].id

        criterion = client.get(
            "/search/",
            params={
                "q": (
                    f"TKT-{records['ticket'].workspace_ticket_number:03d}"
                    f"-AC-{records['criterion'].reference_number:03d}"
                )
            },
        ).json()
        assert criterion["acceptance_criteria"][0]["id"] == records["criterion"].id
    finally:
        close_search_client(engine, db)


def test_search_filters_terminal_deferred_and_archived_work():
    engine, db, client, _records = build_search_client()
    try:
        assert client.get(
            "/search/", params={"q": "Completed discovery"}
        ).json()["tickets"] == []
        assert len(client.get(
            "/search/",
            params={"q": "Completed discovery", "include_completed": True},
        ).json()["tickets"]) == 1

        assert client.get(
            "/search/", params={"q": "Deferred criterion"}
        ).json()["acceptance_criteria"] == []
        assert len(client.get(
            "/search/",
            params={"q": "Deferred criterion", "include_deferred": True},
        ).json()["acceptance_criteria"]) == 1

        assert client.get(
            "/search/", params={"q": "Archived migration"}
        ).json()["tickets"] == []
        archived = client.get(
            "/search/",
            params={"q": "Archived migration", "include_archived": True},
        ).json()
        assert archived["tickets"][0]["archived"] is True
    finally:
        close_search_client(engine, db)


def test_private_work_remains_searchable_to_authorized_workspace_member():
    engine, db, client, records = build_search_client()
    try:
        payload = client.get("/search/", params={"q": "Private"}).json()
        assert records["private_project"].id in {
            item["id"] for item in payload["projects"]
        }
        assert any(item["private"] is True for item in payload["tickets"])
    finally:
        close_search_client(engine, db)


def test_search_never_returns_or_counts_another_workspace():
    engine, db, client, _records = build_search_client()
    try:
        payload = client.get("/search/", params={"q": "Forbidden Needle"}).json()
        assert payload["total"] == 0
        assert result_ids(payload) == set()
        assert payload["truncated"] is False
    finally:
        close_search_client(engine, db)


def test_search_requires_authentication_and_a_meaningful_query():
    engine, db, client, _records = build_search_client()
    try:
        assert client.get("/search/", params={"q": "a"}).status_code == 422
        assert client.get("/search/", params={"q": "  "}).status_code == 422
        client.cookies.clear()
        assert client.get("/search/", params={"q": "Telaryn"}).status_code == 401
    finally:
        close_search_client(engine, db)


def test_search_is_bounded_and_reports_truncation():
    engine, db, client, _records = build_search_client()
    try:
        payload = client.get(
            "/search/",
            params={"q": "Search", "limit": 2},
        ).json()
        assert payload["total"] == 2
        assert payload["truncated"] is True
    finally:
        close_search_client(engine, db)


def test_exact_references_ignore_lifecycle_filters_but_text_does_not():
    engine, db, client, records = build_search_client()
    try:
        ticket = records["ticket"]
        project = records["project"]
        project.archived_at = datetime(2026, 9, 14, 8, 0)
        records["criterion"].completed = True
        records["subtask"].status = SubtaskStatus.DEFERRED
        db.commit()
        for status in (TicketStatus.DONE, TicketStatus.CANCELLED):
            ticket.status = status
            db.commit()
            for reference in (
                f"TKT-{ticket.workspace_ticket_number:03d}",
                ticket.public_id.lower(),
            ):
                response = client.get("/search/", params={
                    "q": reference, "status": "ready", "limit": 1,
                })
                assert response.status_code == 200
                payload = response.json()
                assert payload["total"] == 1
                assert payload["tickets"][0]["id"] == ticket.id
                assert payload["tickets"][0]["status"] == status.value
                assert payload["tickets"][0]["archived"] is True

        cases = [
            (f"PRJ-{project.workspace_project_number:03d}", "projects", project.id),
            (project.public_id, "projects", project.id),
            (f"TKT-{ticket.workspace_ticket_number:03d}-AC-{records['criterion'].reference_number:03d}",
             "acceptance_criteria", records["criterion"].id),
            (f"{ticket.public_id}-ST-{records['subtask'].reference_number:03d}",
             "subtasks", records["subtask"].id),
        ]
        for reference, group, identifier in cases:
            payload = client.get("/search/", params={"q": reference}).json()
            assert payload["total"] == 1
            assert payload[group][0]["id"] == identifier
        assert client.get("/search/", params={"q": ticket.title}).json()["total"] == 0
    finally:
        close_search_client(engine, db)


def test_exact_public_reference_cannot_cross_workspace_boundary():
    engine, db, client, records = build_search_client()
    try:
        outsider = db.query(Ticket).filter(
            Ticket.workspace_id != records["ticket"].workspace_id,
        ).one()
        outsider.status = TicketStatus.DONE
        db.commit()
        for reference in (
            outsider.public_id,
            f"{outsider.public_id}-AC-001",
            outsider.project.public_id,
        ):
            payload = client.get("/search/", params={"q": reference}).json()
            assert payload["total"] == 0
            assert result_ids(payload) == set()
    finally:
        close_search_client(engine, db)

