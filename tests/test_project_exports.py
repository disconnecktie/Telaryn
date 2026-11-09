"""Project exports reuse the Ticket serializer and stay within workspace boundaries."""

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project import Project
from app.models.project_ai_policy_event import ProjectAIPolicyEvent
from app.models.project_lifecycle_event import ProjectLifecycleEvent
from app.models.subtask import Subtask
from app.models.ticket import Ticket
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from tests.test_workspace_authorization import (
    build_authorization_client,
    close_authorization_client,
)


def contains_internal_identifiers(value):
    if isinstance(value, dict):
        return any(
            key == "id" or key.endswith("_id") or contains_internal_identifiers(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_internal_identifiers(item) for item in value)
    return False


def test_project_export_contains_all_member_tickets_and_canonical_history():
    engine, db, client, records = build_authorization_client()
    try:
        project = records["jay_project"]
        owner_ticket = records["jay_ticket"]
        project.description = "Purposeful work\nwith real newlines"
        project.purpose = "Track the project end-to-end"
        project.why_it_matters = "Reliable handoff"
        project.life_context = "work"
        project.ai_context_enabled = False
        owner_ticket.ai_context_enabled = False
        owner_ticket.description = "A private ticket remains exportable by its owner"

        second = Ticket(
            workspace_id=project.workspace_id,
            project_id=project.id,
            title="Second Ticket",
        )
        unrelated_project = Project(name="Another Project", workspace_id=project.workspace_id)
        db.add_all([second, unrelated_project])
        db.flush()
        other_in_workspace = Ticket(
            workspace_id=project.workspace_id,
            project_id=unrelated_project.id,
            title="Unrelated project ticket",
        )
        unassigned = Ticket(
            workspace_id=project.workspace_id,
            project_id=None,
            title="Unassigned ticket",
        )
        db.add_all([
            other_in_workspace,
            unassigned,
            AcceptanceCriterion(ticket_id=owner_ticket.id, text="Criterion one"),
            Subtask(ticket_id=owner_ticket.id, title="Subtask one"),
            TicketUpdateEntry(
                ticket_id=owner_ticket.id,
                content="Work was validated",
                actor_user_id=records["jay"].id,
            ),
            TicketStatusEvent(
                ticket_id=owner_ticket.id,
                from_status="ready",
                to_status="in_progress",
                actor_user_id=records["jay"].id,
                note="Started",
            ),
            ProjectLifecycleEvent(
                workspace_id=project.workspace_id,
                project_id=project.id,
                actor_user_id=records["jay"].id,
                action="life_context_changed",
                previous_life_context="unclassified",
                new_life_context="work",
            ),
            ProjectAIPolicyEvent(
                workspace_id=project.workspace_id,
                project_id=project.id,
                actor_id=records["jay"].id,
                previous_ai_context_enabled=True,
                new_ai_context_enabled=False,
            ),
        ])
        db.commit()

        response = client.get(f"/projects/{project.id}/export.json")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert response.headers["content-disposition"] == (
            f'attachment; filename="prj-{project.workspace_project_number:03d}-export.json"'
        )
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        document = response.json()
        assert document["schema"] == "atlas.project-export"
        assert document["schema_version"] == "1.0"
        assert document["ticket_schema_version"] == "1.0"
        assert document["exported_at"].endswith("Z")
        assert document["project"]["name"] == "Jay Project"
        assert document["project"]["description"] == project.description
        assert document["project"]["purpose"] == project.purpose
        assert document["project"]["why_it_matters"] == project.why_it_matters
        assert document["project"]["life_context"] == "work"
        assert document["project"]["private"] is True
        assert document["project"]["archived"] is False
        assert document["project"]["public_reference"] == project.public_id
        assert document["ticket_count"] == 2
        assert [item["ticket"]["title"] for item in document["tickets"]] == [
            "Jay Ticket", "Second Ticket",
        ]
        ticket_snapshot = document["tickets"][0]
        assert ticket_snapshot["schema"] == "atlas.ticket-export"
        assert ticket_snapshot["ticket"]["public_reference"] == owner_ticket.public_id
        assert ticket_snapshot["ticket"]["private"] is True
        assert ticket_snapshot["acceptance_criteria"][0]["text"] == "Criterion one"
        assert ticket_snapshot["subtasks"][0]["title"] == "Subtask one"
        assert ticket_snapshot["updates"][0]["content"] == "Work was validated"
        assert ticket_snapshot["status_history"][0]["note"] == "Started"
        assert document["lifecycle_history"][0]["action"] == "life_context_changed"
        assert document["lifecycle_history"][0]["author"] == "Jay"
        assert document["ai_context_policy_history"][0]["new_ai_context_enabled"] is False
        assert not contains_internal_identifiers(document)
        assert "Private Other Ticket" not in response.text
        assert "Unassigned ticket" not in response.text
        assert "Unrelated project ticket" not in response.text
    finally:
        close_authorization_client(engine, db)


def test_empty_and_archived_projects_can_be_exported_without_mutation():
    engine, db, client, records = build_authorization_client()
    try:
        project = Project(
            workspace_id=records["jay_project"].workspace_id,
            name="Archived Empty",
            ai_context_enabled=False,
            archive_reason="completed",
            archive_reason_note="Archived intentionally",
        )
        db.add(project)
        db.flush()
        from app.core.time import utc_now
        project.archived_at = utc_now()
        db.commit()
        initial_updated = project.updated_at

        response = client.get(f"/projects/{project.id}/export.json")
        assert response.status_code == 200
        body = response.json()
        assert body["project"]["archived"] is True
        assert body["project"]["archive_reason"] == "completed"
        assert body["project"]["archive_reason_note"] == "Archived intentionally"
        assert body["project"]["archived_at"] is not None
        assert body["ticket_count"] == 0
        assert body["tickets"] == []
        assert body["lifecycle_history"] == []
        db.refresh(project)
        assert project.updated_at == initial_updated
    finally:
        close_authorization_client(engine, db)


def test_project_export_requires_session_and_hides_other_workspaces():
    engine, db, client, records = build_authorization_client()
    try:
        other_project_id = records["other_project"].id
        assert client.get(f"/projects/{other_project_id}/export.json").status_code == 404
        assert client.get("/projects/999999/export.json").status_code == 404
        client.cookies.clear()
        assert client.get(f"/projects/{records['jay_project'].id}/export.json").status_code == 401
    finally:
        close_authorization_client(engine, db)
