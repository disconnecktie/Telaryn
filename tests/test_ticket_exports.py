"""Verify authorized Ticket exports remain complete, portable, and isolated."""

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.subtask import Subtask
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from tests.test_workspace_authorization import (
    build_authorization_client,
    close_authorization_client,
)


def _contains_forbidden_identifier(value):
    if isinstance(value, dict):
        return any(
            key == "id" or key.endswith("_id") or _contains_forbidden_identifier(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_identifier(item) for item in value)
    return False


def test_json_export_uses_stable_references_and_excludes_internal_boundaries():
    engine, db, client, records = build_authorization_client()
    try:
        ticket = records["jay_ticket"]
        ticket.description = "First paragraph.\n\nSecond paragraph."
        ticket.ai_context_enabled = False
        criterion = AcceptanceCriterion(ticket_id=ticket.id, text="Keep the record portable")
        subtask = Subtask(ticket_id=ticket.id, title="Generate both formats", description="JSON\nPDF")
        update = TicketUpdateEntry(ticket_id=ticket.id, content="Export work completed", actor_user_id=records["jay"].id)
        status = TicketStatusEvent(ticket_id=ticket.id, from_status="ready", to_status="in_progress", note="Started export work", actor_user_id=records["jay"].id)
        activity = TicketActivityEvent(
            ticket_id=ticket.id,
            event_type="ticket_updated",
            actor_type="user",
            actor_id=str(records["jay"].id),
            field_name="description",
            previous_value={"project_id": 999, "description": "Old"},
            new_value={"ticket_id": ticket.id, "description": ticket.description},
        )
        db.add_all([criterion, subtask, update, status, activity])
        db.commit()

        response = client.get(f"/tickets/{ticket.id}/export.json")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        assert "attachment;" in response.headers["content-disposition"]
        payload = response.json()
        assert payload["schema"] == "atlas.ticket-export"
        assert payload["schema_version"] == "1.0"
        assert payload["ticket"]["description"] == "First paragraph.\n\nSecond paragraph."
        assert payload["ticket"]["private"] is True
        assert payload["ticket"]["public_reference"] == ticket.public_id
        assert payload["project"]["public_reference"] == records["jay_project"].public_id
        assert payload["acceptance_criteria"][0]["reference"] == "AC-001"
        assert payload["subtasks"][0]["reference"] == "ST-001"
        assert payload["updates"][0]["content"] == "Export work completed"
        assert payload["status_history"][0]["note"] == "Started export work"
        exported_update = next(
            item for item in payload["activity_history"]
            if item["event_type"] == "ticket_updated"
        )
        assert exported_update["new_value"] == {"description": ticket.description}
        assert not _contains_forbidden_identifier(payload)
    finally:
        close_authorization_client(engine, db)


def test_pdf_export_is_a_downloadable_human_readable_document():
    engine, db, client, records = build_authorization_client()
    try:
        ticket = records["jay_ticket"]
        response = client.get(f"/tickets/{ticket.id}/export.pdf")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.headers["content-disposition"].endswith('.pdf"')
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 1000
    finally:
        close_authorization_client(engine, db)


def test_ticket_exports_require_authentication_and_hide_other_workspaces():
    engine, db, client, records = build_authorization_client()
    try:
        other_ticket_id = records["other_ticket"].id
        assert client.get(f"/tickets/{other_ticket_id}/export.json").status_code == 404
        assert client.get(f"/tickets/{other_ticket_id}/export.pdf").status_code == 404

        client.cookies.clear()
        assert client.get(f"/tickets/{records['jay_ticket'].id}/export.json").status_code == 401
        assert client.get(f"/tickets/{records['jay_ticket'].id}/export.pdf").status_code == 401
    finally:
        close_authorization_client(engine, db)
