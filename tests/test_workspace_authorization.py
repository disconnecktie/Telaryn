"""Attack every ticket resource boundary with a second authenticated workspace."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register the complete SQLAlchemy model graph
from app.ai.factory import get_ai_provider
from app.ai.mock import MockAIProvider
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.ai_review import AIReview, AIReviewStatus
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.project import Project
from app.models.project_ai_policy_event import ProjectAIPolicyEvent
from app.models.project_lifecycle_event import ProjectLifecycleEvent
from app.models.project_review_attempt import ProjectReviewAttempt, ProjectReviewAttemptStatus
from app.models.subtask import Subtask
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import hash_password


ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "correct horse battery staple"


def build_authorization_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)

    jay = User(email="jay@example.com", display_name="Jay", password_hash=hash_password(PASSWORD))
    other = User(email="other@example.com", display_name="Other", password_hash=hash_password(PASSWORD))
    db.add_all([jay, other])
    db.flush()
    jay_workspace = Workspace(name="Jay's Workspace", created_by_user_id=jay.id)
    other_workspace = Workspace(name="Other Workspace", created_by_user_id=other.id)
    db.add_all([jay_workspace, other_workspace])
    db.flush()
    db.add_all([
        WorkspaceMembership(workspace_id=jay_workspace.id, user_id=jay.id, role="owner"),
        WorkspaceMembership(workspace_id=other_workspace.id, user_id=other.id, role="owner"),
    ])

    jay_project = Project(name="Jay Project", workspace_id=jay_workspace.id)
    other_project = Project(name="Private Other Project", workspace_id=other_workspace.id)
    db.add_all([jay_project, other_project])
    db.flush()
    jay_ticket = Ticket(title="Jay Ticket", workspace_id=jay_workspace.id, project_id=jay_project.id)
    other_ticket = Ticket(title="Private Other Ticket", workspace_id=other_workspace.id, project_id=other_project.id)
    db.add_all([jay_ticket, other_ticket])
    db.flush()
    other_criterion = AcceptanceCriterion(ticket_id=other_ticket.id, text="Private criterion")
    other_subtask = Subtask(ticket_id=other_ticket.id, title="Private subtask")
    other_update = TicketUpdateEntry(ticket_id=other_ticket.id, content="Private update", actor_user_id=other.id)
    other_status = TicketStatusEvent(
        ticket_id=other_ticket.id,
        from_status="ready",
        to_status="in_progress",
        actor_user_id=other.id,
    )
    other_activity = TicketActivityEvent(
        ticket_id=other_ticket.id,
        event_type="ticket_created",
        actor_type="user",
        actor_id=str(other.id),
    )
    legacy_activity = TicketActivityEvent(
        ticket_id=jay_ticket.id,
        event_type="ticket_created",
        actor_type="local_user",
        actor_id=None,
    )
    other_review = AIReview(
        ticket_id=other_ticket.id,
        status=AIReviewStatus.COMPLETED,
        provider="mock",
        model="mock-v1",
    )
    other_project_review = ProjectReviewAttempt(
        workspace_id=other_workspace.id,
        project_id=other_project.id,
        requested_by_user_id=other.id,
        snapshot_version="a" * 64,
        successful_snapshot_key="a" * 64,
        status=ProjectReviewAttemptStatus.COMPLETED,
        provider="mock",
        model="mock-v2",
        result={
            "outcome": "no_material_concerns",
            "summary": "Private review",
            "findings": [],
            "risks": [],
            "planning_guidance": [],
            "proposals": [],
            "recommended_focus": None,
        },
    )
    db.add_all([
        other_criterion,
        other_subtask,
        other_update,
        other_status,
        other_activity,
        legacy_activity,
        other_review,
        other_project_review,
    ])
    db.commit()

    def test_db():
        yield db

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_ai_provider] = MockAIProvider
    client = TestClient(app)
    assert client.post(
        "/auth/login",
        headers=ORIGIN,
        json={"email": jay.email, "password": PASSWORD},
    ).status_code == 200
    return engine, db, client, {
        "jay": jay,
        "jay_project": jay_project,
        "jay_ticket": jay_ticket,
        "other": other,
        "other_project": other_project,
        "other_ticket": other_ticket,
        "other_criterion": other_criterion,
        "other_subtask": other_subtask,
        "other_review": other_review,
        "other_project_review": other_project_review,
    }


def close_authorization_client(engine, db):
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_ai_provider, None)
    db.close()
    engine.dispose()


def assert_hidden(response):
    assert response.status_code == 404
    assert response.json()["detail"] in {"Project not found", "Ticket not found"}


def test_cross_workspace_resources_are_hidden_from_reads_and_mutations():
    engine, db, client, records = build_authorization_client()
    try:
        project_id = records["other_project"].id
        ticket_id = records["other_ticket"].id
        criterion_id = records["other_criterion"].id
        subtask_id = records["other_subtask"].id
        review_id = records["other_review"].id

        requests = [
            client.get(f"/projects/{project_id}"),
            client.patch(f"/projects/{project_id}", headers=ORIGIN, json={"name": "Stolen"}),
            client.get(f"/projects/{project_id}/work-overview"),
            client.get(f"/projects/{project_id}/review-context"),
            client.get(f"/projects/{project_id}/reviews/"),
            client.post(f"/projects/{project_id}/reviews/", headers=ORIGIN),
            client.get(
                f"/projects/{project_id}/reviews/{records['other_project_review'].id}"
            ),
            client.get(f"/tickets/{ticket_id}"),
            client.patch(f"/tickets/{ticket_id}", headers=ORIGIN, json={"title": "Stolen"}),
            client.get(f"/tickets/{ticket_id}/status-history"),
            client.get(f"/tickets/{ticket_id}/activity-events"),
            client.get(f"/tickets/{ticket_id}/activity"),
            client.get(f"/tickets/{ticket_id}/acceptance-criteria/"),
            client.post(f"/tickets/{ticket_id}/acceptance-criteria/", headers=ORIGIN, json={"text": "Stolen"}),
            client.put(f"/tickets/{ticket_id}/acceptance-criteria/", headers=ORIGIN, json={"criteria": []}),
            client.patch(f"/tickets/{ticket_id}/acceptance-criteria/{criterion_id}", headers=ORIGIN, json={"text": "Stolen"}),
            client.delete(f"/tickets/{ticket_id}/acceptance-criteria/{criterion_id}?reason=Stolen", headers=ORIGIN),
            client.get(f"/tickets/{ticket_id}/subtasks/"),
            client.post(f"/tickets/{ticket_id}/subtasks/", headers=ORIGIN, json={"title": "Stolen"}),
            client.put(f"/tickets/{ticket_id}/subtasks/", headers=ORIGIN, json={"subtasks": []}),
            client.patch(f"/tickets/{ticket_id}/subtasks/{subtask_id}", headers=ORIGIN, json={"title": "Stolen"}),
            client.delete(f"/tickets/{ticket_id}/subtasks/{subtask_id}?reason=Stolen", headers=ORIGIN),
            client.get(f"/tickets/{ticket_id}/updates/"),
            client.post(f"/tickets/{ticket_id}/updates/", headers=ORIGIN, json={"content": "Stolen"}),
            client.get(f"/tickets/{ticket_id}/ai-reviews/"),
            client.post(f"/tickets/{ticket_id}/ai-reviews/", headers=ORIGIN),
            client.post(f"/tickets/{ticket_id}/ai-reviews/{review_id}/accept", headers=ORIGIN, json={}),
        ]
        for response in requests:
            assert_hidden(response)

        # A valid parent URL cannot be paired with a child owned by another ticket.
        jay_ticket_id = records["jay_ticket"].id
        assert client.patch(
            f"/tickets/{jay_ticket_id}/acceptance-criteria/{criterion_id}",
            headers=ORIGIN,
            json={"text": "Stolen"},
        ).status_code == 404
        assert client.patch(
            f"/tickets/{jay_ticket_id}/subtasks/{subtask_id}",
            headers=ORIGIN,
            json={"title": "Stolen"},
        ).status_code == 404

        assert db.get(Ticket, ticket_id).title == "Private Other Ticket"
        assert db.get(AcceptanceCriterion, criterion_id).text == "Private criterion"
        assert db.get(Subtask, subtask_id).title == "Private subtask"
    finally:
        close_authorization_client(engine, db)


def test_foreign_project_ids_cannot_enter_ticket_or_ai_context():
    engine, db, client, records = build_authorization_client()
    try:
        project_id = records["other_project"].id
        ticket_id = records["jay_ticket"].id
        assert_hidden(client.post(
            "/tickets/",
            headers=ORIGIN,
            json={"title": "Invalid assignment", "project_id": project_id},
        ))
        assert_hidden(client.patch(
            f"/tickets/{ticket_id}",
            headers=ORIGIN,
            json={"project_id": project_id},
        ))
        assert_hidden(client.post(
            "/ai-reviews/draft",
            headers=ORIGIN,
            json={"title": "Private context attack", "project_id": project_id},
        ))
        assert_hidden(client.put(
            f"/tickets/{ticket_id}/drawer-session",
            headers=ORIGIN,
            json={
                "ticket": {
                    "title": "Jay Ticket",
                    "description": None,
                    "priority": "medium",
                    "ticket_type": "task",
                    "status": "ready",
                    "project_id": project_id,
                },
                "acceptance_criteria": [],
                "subtasks": [],
                "note": None,
            },
        ))
    finally:
        close_authorization_client(engine, db)


def test_authenticated_human_activity_is_attributed_without_rewriting_legacy_rows():
    engine, db, client, records = build_authorization_client()
    try:
        ticket = client.post(
            "/tickets/", headers=ORIGIN, json={"title": "Attributed ticket"}
        ).json()
        assert client.patch(
            f"/tickets/{ticket['id']}", headers=ORIGIN, json={"title": "Attributed edit"}
        ).status_code == 200
        assert client.patch(
            f"/tickets/{ticket['id']}", headers=ORIGIN, json={"status": "in_progress"}
        ).status_code == 200
        assert client.post(
            f"/tickets/{ticket['id']}/updates/",
            headers=ORIGIN,
            json={"content": "Attributed update"},
        ).status_code == 201

        activity = client.get(f"/tickets/{ticket['id']}/activity").json()
        assert {item["actor_type"] for item in activity} == {"user"}
        assert {item["actor_id"] for item in activity} == {str(records["jay"].id)}
        assert {item["actor_name"] for item in activity} == {"Jay"}
        assert db.query(TicketStatusEvent).filter_by(ticket_id=ticket["id"]).one().actor_user_id == records["jay"].id
        assert db.query(TicketUpdateEntry).filter_by(ticket_id=ticket["id"]).one().actor_user_id == records["jay"].id

        legacy = client.get(
            f"/tickets/{records['other_ticket'].id}/activity"
        )
        assert legacy.status_code == 404
        # Existing null attribution remains untouched rather than being backfilled.
        legacy_event = db.query(TicketActivityEvent).filter_by(
            ticket_id=records["jay_ticket"].id, actor_type="local_user"
        ).one()
        assert legacy_event.actor_id is None
    finally:
        close_authorization_client(engine, db)


def test_ticket_lists_include_only_the_authenticated_workspace():
    engine, db, client, records = build_authorization_client()
    try:
        tickets = client.get("/tickets/").json()
        projects = client.get("/projects/").json()
        review_context = client.get(
            f"/projects/{records['jay_project'].id}/review-context"
        )
        assert review_context.status_code == 200
        assert review_context.json()["project"]["name"] == "Jay Project"
        assert [ticket["title"] for ticket in review_context.json()["tickets"]] == [
            "Jay Ticket"
        ]
        assert [ticket["title"] for ticket in tickets] == ["Jay Ticket"]
        assert [project["name"] for project in projects] == ["Jay Project"]
        assert client.get("/tickets/999999").status_code == 404
        assert client.get(f"/tickets/{records['other_ticket'].id}").status_code == 404
        my_work = client.get("/my-work/").json()
        surfaced_ids = {
            item["id"]
            for section in (
                "focus_now", "needs_attention", "up_next", "in_review", "recently_completed"
            )
            for item in my_work[section]
        }
        assert surfaced_ids == {records["jay_ticket"].id}
        assert client.patch(
            f"/my-work/tickets/{records['other_ticket'].id}",
            headers=ORIGIN,
            json={"current_focus": True},
        ).status_code == 404
        focused = client.patch(
            f"/my-work/tickets/{records['jay_ticket'].id}",
            headers=ORIGIN,
            json={"current_focus": True},
        )
        assert focused.status_code == 200
        assert focused.json()["current_focus"]["id"] == records["jay_ticket"].id
        db.refresh(records["jay_ticket"])
        assert records["jay_ticket"].status.value == "ready"
    finally:
        close_authorization_client(engine, db)


def test_protected_resource_families_consistently_require_authentication():
    engine, db, client, records = build_authorization_client()
    try:
        assert client.delete("/auth/session", headers=ORIGIN).status_code == 204
        ticket_id = records["jay_ticket"].id
        paths = [
            "/projects/",
            "/my-work/",
            f"/projects/{records['jay_project'].id}/review-context",
            f"/projects/{records['jay_project'].id}/reviews/",
            "/tickets/",
            f"/tickets/{ticket_id}/acceptance-criteria/",
            f"/tickets/{ticket_id}/subtasks/",
            f"/tickets/{ticket_id}/updates/",
            f"/tickets/{ticket_id}/activity",
            f"/tickets/{ticket_id}/ai-reviews/",
        ]
        for path in paths:
            response = client.get(path)
            assert response.status_code == 401
            assert response.json()["detail"] == "Authentication required."
        project_review_post = client.post(
            f"/projects/{records['jay_project'].id}/reviews/",
            headers=ORIGIN,
        )
        assert project_review_post.status_code == 401
        assert project_review_post.json()["detail"] == "Authentication required."
    finally:
        close_authorization_client(engine, db)


def test_project_review_endpoints_scope_attempts_to_requester_and_parent_project():
    engine, db, client, records = build_authorization_client()
    try:
        project_id = records["jay_project"].id
        created = client.post(
            f"/projects/{project_id}/reviews/",
            headers=ORIGIN,
        )
        assert created.status_code == 202
        review_id = created.json()["id"]

        listed = client.get(f"/projects/{project_id}/reviews/")
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [review_id]
        assert client.get(
            f"/projects/{project_id}/reviews/{review_id}"
        ).status_code == 200

        second_project = Project(
            name="Another Jay Project",
            workspace_id=records["jay_project"].workspace_id,
        )
        db.add(second_project)
        db.commit()
        assert client.get(
            f"/projects/{second_project.id}/reviews/{review_id}"
        ).status_code == 404

        other_requester = User(
            email="collaborator@example.com",
            display_name="Collaborator",
            password_hash=hash_password(PASSWORD),
        )
        db.add(other_requester)
        db.flush()
        db.add(
            WorkspaceMembership(
                workspace_id=records["jay_project"].workspace_id,
                user_id=other_requester.id,
                role="member",
            )
        )
        db.flush()
        requester_private = ProjectReviewAttempt(
            workspace_id=records["jay_project"].workspace_id,
            project_id=project_id,
            requested_by_user_id=other_requester.id,
            snapshot_version="b" * 64,
            successful_snapshot_key="b" * 64,
            status=ProjectReviewAttemptStatus.COMPLETED,
            provider="mock",
            model="mock-v2",
            result={
                "outcome": "no_material_concerns",
                "summary": "Requester-private review",
                "findings": [],
                "risks": [],
                "planning_guidance": [],
                "proposals": [],
                "recommended_focus": None,
            },
        )
        db.add(requester_private)
        db.commit()

        assert client.get(
            f"/projects/{project_id}/reviews/{requester_private.id}"
        ).status_code == 404
        assert requester_private.id not in {
            item["id"] for item in client.get(f"/projects/{project_id}/reviews/").json()
        }
    finally:
        close_authorization_client(engine, db)


def test_direct_focus_rejects_ineligible_statuses_without_replacing_focus():
    engine, db, client, records = build_authorization_client()
    try:
        current = records["jay_ticket"]
        assert client.patch(
            f"/my-work/tickets/{current.id}",
            headers=ORIGIN,
            json={"current_focus": True},
        ).status_code == 200
        candidate = Ticket(
            title="Candidate",
            status=TicketStatus.READY,
            workspace_id=records["jay_project"].workspace_id,
            project_id=records["jay_project"].id,
        )
        db.add(candidate)
        db.commit()

        for status in (
            TicketStatus.BLOCKED,
            TicketStatus.REVIEW,
            TicketStatus.DONE,
            TicketStatus.CANCELLED,
        ):
            candidate.status = status
            db.commit()
            response = client.patch(
                f"/my-work/tickets/{candidate.id}",
                headers=ORIGIN,
                json={"current_focus": True},
            )
            assert response.status_code == 409
            assert response.json()["detail"] == (
                "Only Ready or In Progress Tickets can become Current Focus."
            )
            focused = db.query(MyWorkPreference).filter_by(
                user_id=records["jay"].id,
                workspace_id=records["jay_project"].workspace_id,
                is_current_focus=True,
            ).one()
            assert focused.ticket_id == current.id
    finally:
        close_authorization_client(engine, db)


def test_unavailable_ticket_requires_make_available_and_focus():
    engine, db, client, records = build_authorization_client()
    try:
        ticket = records["jay_ticket"]
        preference = MyWorkPreference(
            user_id=records["jay"].id,
            workspace_id=records["jay_project"].workspace_id,
            ticket_id=ticket.id,
            availability_mode=FocusAvailabilityMode.DATE,
            available_on=date(2099, 1, 1),
        )
        db.add(preference)
        db.commit()

        ordinary = client.patch(
            f"/my-work/tickets/{ticket.id}",
            headers=ORIGIN,
            json={"current_focus": True},
        )
        assert ordinary.status_code == 409
        db.refresh(preference)
        assert preference.availability_mode == FocusAvailabilityMode.DATE
        assert preference.is_current_focus is False

        restored = client.patch(
            f"/my-work/tickets/{ticket.id}",
            headers=ORIGIN,
            json={
                "current_focus": True,
                "make_available_and_focus": True,
            },
        )
        assert restored.status_code == 200
        assert restored.json()["current_focus"]["id"] == ticket.id
        db.refresh(preference)
        assert preference.availability_mode == FocusAvailabilityMode.AVAILABLE
        assert preference.is_current_focus is True
    finally:
        close_authorization_client(engine, db)


def test_project_ai_context_policy_is_audited_and_blocks_all_ai_entry_points():
    engine, db, client, records = build_authorization_client()
    try:
        project = records["jay_project"]
        ticket = records["jay_ticket"]

        changed = client.patch(
            f"/projects/{project.id}/ai-context-policy",
            headers=ORIGIN,
            json={"ai_context_enabled": False},
        )
        assert changed.status_code == 200
        assert changed.json()["ai_context_enabled"] is False

        event = db.query(ProjectAIPolicyEvent).filter_by(project_id=project.id).one()
        assert event.workspace_id == project.workspace_id
        assert event.actor_id == records["jay"].id
        assert event.previous_ai_context_enabled is True
        assert event.new_ai_context_enabled is False

        # Private projects still remain readable to workspace members.
        assert client.get(f"/projects/{project.id}/review-context").status_code == 200

        requests = [
            client.post(f"/tickets/{ticket.id}/ai-reviews/", headers=ORIGIN),
            client.post(
                "/ai-reviews/draft",
                headers=ORIGIN,
                json={"title": "Private draft", "project_id": project.id},
            ),
            client.post(f"/projects/{project.id}/reviews/", headers=ORIGIN),
        ]
        for response in requests:
            assert response.status_code == 409
            assert "Private project" in response.json()["detail"]

        unchanged = client.patch(
            f"/projects/{project.id}/ai-context-policy",
            headers=ORIGIN,
            json={"ai_context_enabled": False},
        )
        assert unchanged.status_code == 200
        assert db.query(ProjectAIPolicyEvent).filter_by(project_id=project.id).count() == 1
    finally:
        close_authorization_client(engine, db)


def test_project_ai_context_policy_is_workspace_scoped():
    engine, db, client, records = build_authorization_client()
    try:
        response = client.patch(
            f"/projects/{records['other_project'].id}/ai-context-policy",
            headers=ORIGIN,
            json={"ai_context_enabled": False},
        )
        assert_hidden(response)
        assert records["other_project"].ai_context_enabled is True
        assert db.query(ProjectAIPolicyEvent).count() == 0
    finally:
        close_authorization_client(engine, db)


def test_project_ai_policy_audit_events_are_append_only():
    engine, db, client, records = build_authorization_client()
    try:
        project = records["jay_project"]
        assert client.patch(
            f"/projects/{project.id}/ai-context-policy",
            headers=ORIGIN,
            json={"ai_context_enabled": False},
        ).status_code == 200
        event = db.query(ProjectAIPolicyEvent).one()
        event.new_ai_context_enabled = True
        try:
            db.commit()
            raise AssertionError("Project AI policy audit events must be immutable.")
        except ValueError as error:
            assert "append-only" in str(error)
            db.rollback()
    finally:
        close_authorization_client(engine, db)


def test_private_ticket_stays_visible_but_blocks_its_saved_ai_review():
    engine, db, client, records = build_authorization_client()
    try:
        ticket = records["jay_ticket"]
        made_private = client.patch(
            f"/tickets/{ticket.id}",
            headers=ORIGIN,
            json={"ai_context_enabled": False},
        )
        assert made_private.status_code == 200
        assert made_private.json()["ai_context_enabled"] is False
        assert client.get(f"/tickets/{ticket.id}").status_code == 200

        blocked = client.post(f"/tickets/{ticket.id}/ai-reviews/", headers=ORIGIN)
        assert blocked.status_code == 409
        assert "Private ticket" in blocked.json()["detail"]

        activity = client.get(f"/tickets/{ticket.id}/activity").json()
        assert any(
            item["field_name"] == "ai_context_enabled"
            and item["new_value"] is False
            for item in activity
        )
    finally:
        close_authorization_client(engine, db)


def test_private_ticket_draft_is_rejected_before_provider_selection():
    engine, db, client, _records = build_authorization_client()
    try:
        response = client.post(
            "/ai-reviews/draft",
            headers=ORIGIN,
            json={"title": "Private unsaved ticket", "ai_context_enabled": False},
        )
        assert response.status_code == 409
        assert "Private ticket" in response.json()["detail"]
    finally:
        close_authorization_client(engine, db)


def test_ticket_identifiers_are_immutable_and_workspace_scoped():
    engine, db, client, records = build_authorization_client()
    try:
        existing = records["jay_ticket"]
        other_workspace_ticket = records["other_ticket"]
        assert existing.workspace_ticket_number == other_workspace_ticket.workspace_ticket_number
        assert existing.public_id != other_workspace_ticket.public_id

        first = client.post(
            "/tickets/", headers=ORIGIN, json={"title": "First identified Ticket"}
        )
        second = client.post(
            "/tickets/", headers=ORIGIN, json={"title": "Second identified Ticket"}
        )
        assert first.status_code == 201
        assert second.status_code == 201

        first_ticket = first.json()
        second_ticket = second.json()
        assert first_ticket["public_id"].startswith("TKT-")
        assert first_ticket["public_id"] != second_ticket["public_id"]
        assert (
            second_ticket["workspace_ticket_number"]
            == first_ticket["workspace_ticket_number"] + 1
        )

        updated = client.patch(
            f"/tickets/{first_ticket['id']}",
            headers=ORIGIN,
            json={"title": "Renamed identified Ticket"},
        )
        assert updated.status_code == 200
        assert updated.json()["public_id"] == first_ticket["public_id"]
        assert (
            updated.json()["workspace_ticket_number"]
            == first_ticket["workspace_ticket_number"]
        )
        assert client.get(
            f"/tickets/public/{first_ticket['public_id']}"
        ).json()["id"] == first_ticket["id"]
        assert client.get(
            f"/tickets/public/{other_workspace_ticket.public_id}"
        ).status_code == 404
    finally:
        close_authorization_client(engine, db)


def test_collaboration_references_are_scoped_immutable_and_hierarchical():
    engine, db, client, records = build_authorization_client()
    try:
        first_project = records["jay_project"]
        other_project = records["other_project"]
        assert first_project.workspace_project_number == other_project.workspace_project_number == 1
        assert first_project.public_id.startswith("PRJ-")
        assert len(first_project.public_id) == 18
        assert client.get(f"/projects/public/{first_project.public_id}").json()["id"] == first_project.id
        assert client.get(f"/projects/public/{other_project.public_id}").status_code == 404

        created_project = client.post("/projects/", headers=ORIGIN, json={"name": "Second Jay Project"})
        assert created_project.status_code == 201
        assert created_project.json()["workspace_project_number"] == 2
        assert len(created_project.json()["public_id"]) == 18

        ticket = client.post("/tickets/", headers=ORIGIN, json={"title": "Collaborative ticket"}).json()
        assert ticket["workspace_ticket_number"] == 2
        assert ticket["public_id"].startswith("TKT-")
        assert len(ticket["public_id"]) == 18

        criterion = client.post(
            f"/tickets/{ticket['id']}/acceptance-criteria/", headers=ORIGIN, json={"text": "It is reviewable"}
        )
        subtask = client.post(
            f"/tickets/{ticket['id']}/subtasks/", headers=ORIGIN, json={"title": "Implement it"}
        )
        assert criterion.status_code == 201
        assert subtask.status_code == 201
        assert criterion.json()["reference_number"] == 1
        assert subtask.json()["reference_number"] == 1

        assert client.patch(
            f"/tickets/{ticket['id']}", headers=ORIGIN, json={"title": "Renamed ticket"}
        ).json()["public_id"] == ticket["public_id"]
        assert client.get(f"/tickets/public/{ticket['public_id']}").status_code == 200
    finally:
        close_authorization_client(engine, db)

def test_project_archival_preserves_work_and_removes_active_context():
    engine, db, client, records = build_authorization_client()
    try:
        project = records["jay_project"]
        ticket = records["jay_ticket"]
        membership = db.query(WorkspaceMembership).filter_by(
            workspace_id=project.workspace_id,
            user_id=records["jay"].id,
        ).one()
        membership.default_project_id = project.id
        preference = MyWorkPreference(
            user_id=records["jay"].id,
            workspace_id=project.workspace_id,
            ticket_id=ticket.id,
            is_current_focus=True,
        )
        db.add(preference)
        db.commit()

        missing_reason = client.post(f"/projects/{project.id}/archive", headers=ORIGIN)
        assert missing_reason.status_code == 422
        invalid_other = client.post(
            f"/projects/{project.id}/archive",
            headers=ORIGIN,
            json={"archive_reason": "other"},
        )
        assert invalid_other.status_code == 422

        archived = client.post(
            f"/projects/{project.id}/archive",
            headers=ORIGIN,
            json={
                "archive_reason": "completed",
                "archive_reason_note": "All intended outcomes were delivered.",
            },
        )
        assert archived.status_code == 200
        assert archived.json()["archived_at"] is not None
        assert archived.json()["archived_by_user_id"] == records["jay"].id
        assert archived.json()["archive_reason"] == "completed"
        assert archived.json()["archive_report_eligible_by_default"] is True

        db.refresh(project)
        db.refresh(ticket)
        db.refresh(membership)
        db.refresh(preference)
        assert ticket.project_id == project.id
        assert membership.default_project_id is None
        assert preference.is_current_focus is False

        assert client.get("/projects/").json() == []
        assert [item["id"] for item in client.get(
            "/projects/?include_archived=true"
        ).json()] == [project.id]
        assert client.get("/tickets/").json() == []
        assert client.get(f"/tickets/{ticket.id}").status_code == 200
        assert client.get("/my-work/").json()["current_focus"] is None

        rejected = client.post(
            "/tickets/",
            headers=ORIGIN,
            json={"title": "Do not assign", "project_id": project.id},
        )
        assert rejected.status_code == 409
        assert "Archived Projects cannot receive Tickets" in rejected.json()["detail"]
        assert client.patch(
            f"/projects/{project.id}",
            headers=ORIGIN,
            json={"name": "Do not edit"},
        ).status_code == 409
        assert client.patch(
            f"/my-work/tickets/{ticket.id}",
            headers=ORIGIN,
            json={"current_focus": True},
        ).status_code == 409

        events = client.get(f"/projects/{project.id}/lifecycle-events").json()
        assert [event["action"] for event in events] == ["archived"]
        assert events[0]["actor_user_id"] == records["jay"].id
        assert events[0]["archive_reason"] == "completed"
        assert events[0]["archive_reason_note"] == "All intended outcomes were delivered."
        assert db.query(ProjectLifecycleEvent).filter_by(
            project_id=project.id
        ).count() == 1

        classified = client.put(
            f"/projects/{project.id}/archive-classification",
            headers=ORIGIN,
            json={
                "archive_reason": "superseded",
                "archive_reason_note": "Replaced by a cleaner Project.",
            },
        )
        assert classified.status_code == 200
        assert classified.json()["archived_at"] is not None
        assert classified.json()["archive_reason"] == "superseded"
        assert classified.json()["archive_report_eligible_by_default"] is False
        events = client.get(f"/projects/{project.id}/lifecycle-events").json()
        assert [event["action"] for event in events] == [
            "archive_classified",
            "archived",
        ]
        assert events[0]["archive_reason"] == "superseded"
        assert events[0]["archive_reason_note"] == "Replaced by a cleaner Project."

        unchanged = client.put(
            f"/projects/{project.id}/archive-classification",
            headers=ORIGIN,
            json={
                "archive_reason": "superseded",
                "archive_reason_note": "Replaced by a cleaner Project.",
            },
        )
        assert unchanged.status_code == 200
        assert db.query(ProjectLifecycleEvent).filter_by(
            project_id=project.id
        ).count() == 2

        restored = client.post(f"/projects/{project.id}/restore", headers=ORIGIN)
        assert restored.status_code == 200
        assert restored.json()["archived_at"] is None
        assert restored.json()["archived_by_user_id"] is None
        assert restored.json()["archive_reason"] is None
        assert restored.json()["archive_reason_note"] is None
        assert restored.json()["archive_report_eligible_by_default"] is False
        assert [item["id"] for item in client.get("/projects/").json()] == [project.id]
        assert [item["id"] for item in client.get("/tickets/").json()] == [ticket.id]
        assert client.post(
            "/tickets/",
            headers=ORIGIN,
            json={"title": "Assign after restore", "project_id": project.id},
        ).status_code == 201
        rejected_classification = client.put(
            f"/projects/{project.id}/archive-classification",
            headers=ORIGIN,
            json={"archive_reason": "completed"},
        )
        assert rejected_classification.status_code == 409
        events = client.get(f"/projects/{project.id}/lifecycle-events").json()
        assert [event["action"] for event in events] == [
            "restored",
            "archive_classified",
            "archived",
        ]
    finally:
        close_authorization_client(engine, db)




def test_archived_project_work_is_readable_but_all_mutations_are_blocked():
    engine, db, client, records = build_authorization_client()
    try:
        project = records["jay_project"]
        ticket = records["jay_ticket"]
        criterion = AcceptanceCriterion(ticket_id=ticket.id, text="Preserved")
        subtask = Subtask(ticket_id=ticket.id, title="Preserved")
        db.add_all([criterion, subtask])
        db.commit()
        assert client.post(
            f"/projects/{project.id}/archive",
            headers=ORIGIN,
            json={"archive_reason": "cancelled"},
        ).status_code == 200

        assert client.get(f"/tickets/{ticket.id}").status_code == 200
        assert client.get(
            f"/tickets/{ticket.id}/acceptance-criteria/"
        ).status_code == 200
        assert client.get(f"/tickets/{ticket.id}/subtasks/").status_code == 200
        assert [item["id"] for item in client.get(
            "/tickets/?include_archived=true"
        ).json()] == [ticket.id]

        blocked_requests = [
            client.patch(
                f"/tickets/{ticket.id}",
                headers=ORIGIN,
                json={"title": "Blocked edit"},
            ),
            client.put(
                f"/tickets/{ticket.id}/drawer-session",
                headers=ORIGIN,
                json={
                    "ticket": {
                        "title": ticket.title,
                        "description": ticket.description,
                        "priority": ticket.priority.value,
                        "ticket_type": ticket.ticket_type.value,
                        "status": ticket.status.value,
                        "project_id": project.id,
                        "ai_context_enabled": True,
                    },
                    "acceptance_criteria": [],
                    "subtasks": [],
                },
            ),
            client.post(
                f"/tickets/{ticket.id}/acceptance-criteria/",
                headers=ORIGIN,
                json={"text": "Blocked criterion"},
            ),
            client.patch(
                f"/tickets/{ticket.id}/acceptance-criteria/{criterion.id}",
                headers=ORIGIN,
                json={"completed": True},
            ),
            client.post(
                f"/tickets/{ticket.id}/subtasks/",
                headers=ORIGIN,
                json={"title": "Blocked subtask"},
            ),
            client.patch(
                f"/tickets/{ticket.id}/subtasks/{subtask.id}",
                headers=ORIGIN,
                json={"status": "done"},
            ),
            client.post(
                f"/tickets/{ticket.id}/updates/",
                headers=ORIGIN,
                json={"content": "Blocked update"},
            ),
            client.post(
                f"/tickets/{ticket.id}/ai-reviews/",
                headers=ORIGIN,
            ),
            client.post(
                f"/projects/{project.id}/reviews/",
                headers=ORIGIN,
            ),
        ]
        assert {response.status_code for response in blocked_requests} == {409}
        assert all("archived" in response.json()["detail"].lower() for response in blocked_requests)
    finally:
        close_authorization_client(engine, db)

def test_project_archival_is_workspace_scoped_and_lifecycle_is_append_only():
    engine, db, client, records = build_authorization_client()
    try:
        other_project = records["other_project"]
        assert client.post(
            f"/projects/{other_project.id}/archive",
            headers=ORIGIN,
            json={"archive_reason": "superseded"},
        ).status_code == 404
        assert client.get(
            f"/projects/{other_project.id}/lifecycle-events"
        ).status_code == 404

        project = records["jay_project"]
        assert client.post(
            f"/projects/{project.id}/archive",
            headers=ORIGIN,
            json={"archive_reason": "test_development"},
        ).status_code == 200
        event = db.query(ProjectLifecycleEvent).filter_by(project_id=project.id).one()
        event.action = "restored"
        try:
            db.commit()
            raise AssertionError("Project lifecycle events must remain immutable.")
        except ValueError as error:
            assert "append-only" in str(error)
            db.rollback()
    finally:
        close_authorization_client(engine, db)

