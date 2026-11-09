"""Regression coverage for immutable audit records and the unified timeline."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers every model with Base metadata
from app.api.tickets import create_ticket, update_ticket
from app.api.acceptance_criteria import (
    create_acceptance_criterion,
    delete_acceptance_criterion,
    update_acceptance_criterion,
)
from app.api.subtasks import create_subtask, delete_subtask, update_subtask
from app.api.ticket_updates import create_ticket_update
from app.db.base import Base
from app.models.ticket import TicketPriority, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.ticket_update_entry import TicketUpdateEntryCreate
from app.schemas.acceptance_criterion import AcceptanceCriterionCreate, AcceptanceCriterionUpdate
from app.schemas.subtask import SubtaskCreate, SubtaskUpdate
from app.services.ticket_activity import list_ticket_activity


class TicketActivityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _events(self, ticket_id: int) -> list[TicketActivityEvent]:
        statement = (
            select(TicketActivityEvent)
            .where(TicketActivityEvent.ticket_id == ticket_id)
            .order_by(TicketActivityEvent.id)
        )
        return list(self.db.scalars(statement).all())

    def test_creation_and_meaningful_field_changes_are_recorded(self) -> None:
        ticket = create_ticket(
            TicketCreate(title="Original", description="Initial scope"),
            self.db,
        )

        update_ticket(
            ticket.id,
            TicketUpdate(
                title="Revised",
                description="Updated scope",
                priority=TicketPriority.HIGH,
            ),
            self.db,
        )
        update_ticket(
            ticket.id,
            TicketUpdate(
                status=TicketStatus.IN_PROGRESS,
                status_note="Work started",
            ),
            self.db,
        )

        events = self._events(ticket.id)
        self.assertEqual(events[0].event_type, "ticket_created")

        changes = {
            event.field_name: event
            for event in events
            if event.event_type == "ticket_field_changed"
        }
        self.assertEqual(changes["title"].previous_value, "Original")
        self.assertEqual(changes["title"].new_value, "Revised")
        self.assertEqual(changes["description"].previous_value, "Initial scope")
        self.assertEqual(changes["description"].new_value, "Updated scope")
        self.assertEqual(changes["priority"].previous_value, "medium")
        self.assertEqual(changes["priority"].new_value, "high")
        self.assertNotIn("status", changes)

        timeline = list_ticket_activity(self.db, ticket_id=ticket.id)
        status_change = next(
            item for item in timeline if item.event_type == "status_changed"
        )
        self.assertEqual(status_change.previous_value, "ready")
        self.assertEqual(status_change.new_value, "in_progress")
        self.assertEqual(status_change.note, "Work started")
        self.assertEqual(status_change.actor_type, "local_user")

    def test_unified_timeline_combines_sources_newest_first(self) -> None:
        ticket = create_ticket(TicketCreate(title="Timeline"), self.db)
        update_ticket(
            ticket.id,
            TicketUpdate(priority=TicketPriority.HIGH),
            self.db,
        )
        create_ticket_update(
            ticket.id,
            TicketUpdateEntryCreate(content="Work is underway."),
            self.db,
        )

        timeline = list_ticket_activity(self.db, ticket_id=ticket.id)

        self.assertEqual(timeline[0].event_type, "ticket_update_added")
        self.assertEqual(timeline[0].content, "Work is underway.")
        self.assertIn(
            "ticket_field_changed",
            [item.event_type for item in timeline],
        )
        self.assertEqual(timeline[-1].event_type, "ticket_created")

    def test_unchanged_fields_do_not_create_activity_noise(self) -> None:
        ticket = create_ticket(TicketCreate(title="Unchanged"), self.db)

        update_ticket(
            ticket.id,
            TicketUpdate(title="Unchanged", priority=TicketPriority.MEDIUM),
            self.db,
        )

        self.assertEqual(len(self._events(ticket.id)), 1)

    def test_activity_events_cannot_be_modified(self) -> None:
        ticket = create_ticket(TicketCreate(title="Immutable"), self.db)
        event = self._events(ticket.id)[0]
        event.note = "tampered"

        with self.assertRaisesRegex(ValueError, "append-only and immutable"):
            self.db.commit()

    def test_ticket_structure_changes_include_human_readable_snapshots(self) -> None:
        ticket = create_ticket(TicketCreate(title="Structured work"), self.db)
        criterion = create_acceptance_criterion(
            ticket.id,
            AcceptanceCriterionCreate(text="Original criterion", sort_order=1),
            self.db,
        )
        subtask = create_subtask(
            ticket.id,
            SubtaskCreate(title="Original subtask", sort_order=1),
            self.db,
        )
        update_acceptance_criterion(
            ticket.id,
            criterion.id,
            AcceptanceCriterionUpdate(text="Revised criterion"),
            self.db,
        )
        update_subtask(
            ticket.id,
            subtask.id,
            SubtaskUpdate(title="Revised subtask"),
            self.db,
        )
        delete_acceptance_criterion(
            ticket.id,
            criterion.id,
            reason="Criterion removed during snapshot test.",
            db=self.db,
        )
        delete_subtask(
            ticket.id,
            subtask.id,
            reason="Subtask removed during snapshot test.",
            db=self.db,
        )

        events = {event.event_type: event for event in self._events(ticket.id)}
        self.assertEqual(events["acceptance_criterion_added"].new_value["text"], "Original criterion")
        self.assertEqual(events["acceptance_criterion_updated"].previous_value["text"], "Original criterion")
        self.assertEqual(events["acceptance_criterion_updated"].new_value["text"], "Revised criterion")
        self.assertEqual(events["acceptance_criterion_removed"].previous_value["text"], "Revised criterion")
        self.assertEqual(events["subtask_added"].new_value["title"], "Original subtask")
        self.assertEqual(events["subtask_updated"].new_value["title"], "Revised subtask")
        self.assertEqual(events["subtask_removed"].previous_value["title"], "Revised subtask")


if __name__ == "__main__":
    unittest.main()
