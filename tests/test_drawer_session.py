"""Regression coverage for validation and atomic drawer-session persistence."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.tickets import create_ticket, save_ticket_drawer_session
from app.db.base import Base
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.subtask import Subtask
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from app.schemas.drawer_session import (
    DrawerCriterionDraft,
    DrawerSessionCommit,
    DrawerSubtaskDraft,
    DrawerTicketDraft,
)
from app.schemas.ticket import TicketActivityEventRead, TicketCreate
from app.services.ticket_activity import list_ticket_activity


class DrawerSessionTests(unittest.TestCase):
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

    def test_full_drawer_commit_creates_one_event(self) -> None:
        ticket = create_ticket(TicketCreate(title="Original"), self.db)
        result = save_ticket_drawer_session(
            ticket.id,
            DrawerSessionCommit(
                ticket=DrawerTicketDraft(
                    title="Revised",
                    description="One reviewed transaction",
                    priority="high",
                    ticket_type="development",
                    status="ready",
                    project_id=None,
                ),
                acceptance_criteria=[
                    DrawerCriterionDraft(text="The transaction is atomic", completed=True)
                ],
                subtasks=[DrawerSubtaskDraft(title="Verify activity", status="done")],
            ),
            self.db,
        )

        events = list(self.db.scalars(select(TicketActivityEvent).where(
            TicketActivityEvent.ticket_id == ticket.id
        ).order_by(TicketActivityEvent.id)).all())
        drawer_events = [event for event in events if event.event_type == "drawer_session_committed"]
        self.assertEqual(len(drawer_events), 1)
        self.assertEqual(result.ticket.title, "Revised")
        self.assertTrue(result.acceptance_criteria[0].completed)
        self.assertEqual(result.subtasks[0].status.value, "done")
        self.assertEqual(drawer_events[0].previous_value["ticket"]["title"], "Original")
        self.assertEqual(drawer_events[0].new_value["ticket"]["title"], "Revised")

    def test_transferred_update_is_atomic_and_not_duplicated_in_drawer_activity(self) -> None:
        ticket = create_ticket(TicketCreate(title="Atomic narrative"), self.db)

        result = save_ticket_drawer_session(
            ticket.id,
            DrawerSessionCommit(
                ticket=DrawerTicketDraft(
                    title=ticket.title,
                    description=None,
                    priority="medium",
                    ticket_type="task",
                    status="done",
                    project_id=None,
                ),
                acceptance_criteria=[
                    DrawerCriterionDraft(text="Document the result", completed=True)
                ],
                subtasks=[],
                update_content="Completed the reviewed work and recorded the outcome.",
            ),
            self.db,
        )

        self.assertEqual(result.ticket.status.value, "done")
        updates = list(self.db.scalars(select(TicketUpdateEntry).where(
            TicketUpdateEntry.ticket_id == ticket.id
        )).all())
        self.assertEqual([update.content for update in updates], [
            "Completed the reviewed work and recorded the outcome."
        ])
        status_event = self.db.scalar(select(TicketStatusEvent).where(
            TicketStatusEvent.ticket_id == ticket.id
        ))
        self.assertEqual(status_event.note, updates[0].content)
        drawer_event = self.db.scalar(select(TicketActivityEvent).where(
            TicketActivityEvent.event_type == "drawer_session_committed"
        ).order_by(TicketActivityEvent.id.desc()))
        self.assertIsNone(drawer_event.note)

    def test_ticket_creation_groups_initial_structure_in_one_event(self) -> None:
        ticket = create_ticket(
            TicketCreate(
                title="Structured from the start",
                acceptance_criteria=[
                    {"text": "Creation is auditable", "sort_order": 1}
                ],
                subtasks=[
                    {"title": "Verify the timeline", "sort_order": 1}
                ],
            ),
            self.db,
        )

        events = list(self.db.scalars(select(TicketActivityEvent).where(
            TicketActivityEvent.ticket_id == ticket.id
        )).all())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ticket_created")
        self.assertEqual(
            events[0].new_value["acceptance_criteria"][0]["text"],
            "Creation is auditable",
        )
        self.assertEqual(
            events[0].new_value["subtasks"][0]["title"],
            "Verify the timeline",
        )

    def test_invalid_child_id_rolls_back_everything(self) -> None:
        ticket = create_ticket(TicketCreate(title="Original"), self.db)
        with self.assertRaises(Exception):
            save_ticket_drawer_session(
                ticket.id,
                DrawerSessionCommit(
                    ticket=DrawerTicketDraft(
                        title="Must roll back",
                        description=None,
                        priority="medium",
                        ticket_type="task",
                        status="ready",
                        project_id=None,
                    ),
                    acceptance_criteria=[DrawerCriterionDraft(id=999, text="Invalid")],
                    subtasks=[],
                ),
                self.db,
            )
        self.db.refresh(ticket)
        self.assertEqual(ticket.title, "Original")
        self.assertEqual(self.db.scalar(select(AcceptanceCriterion)), None)
        self.assertEqual(self.db.scalar(select(Subtask)), None)

    def test_progress_and_status_share_one_unified_activity_item(self) -> None:
        ticket = create_ticket(TicketCreate(title="Combined update"), self.db)
        result = save_ticket_drawer_session(
            ticket.id,
            DrawerSessionCommit(
                ticket=DrawerTicketDraft(
                    title=ticket.title,
                    description=None,
                    priority="medium",
                    ticket_type="task",
                    status="done",
                    project_id=None,
                ),
                acceptance_criteria=[
                    DrawerCriterionDraft(text="Outcome verified", completed=True)
                ],
                subtasks=[],
                note="Finished and verified together.",
            ),
            self.db,
        )

        self.assertEqual(result.ticket.status.value, "done")
        status_event = self.db.scalar(select(TicketStatusEvent).where(
            TicketStatusEvent.ticket_id == ticket.id
        ))
        self.assertIsNotNone(status_event)
        self.assertEqual(status_event.note, "Finished and verified together.")
        session_event = self.db.scalar(select(TicketActivityEvent).where(
            TicketActivityEvent.event_type == "drawer_session_committed"
        ))
        self.assertEqual(session_event.new_value["status_event_id"], status_event.id)
        visible_types = [item.event_type for item in list_ticket_activity(
            self.db, ticket_id=ticket.id
        )]
        self.assertIn("drawer_session_committed", visible_types)
        self.assertNotIn("status_changed", visible_types)

    def test_legacy_activity_timestamp_serializes_as_utc(self) -> None:
        ticket = create_ticket(TicketCreate(title="Timestamp"), self.db)
        event = self.db.scalar(select(TicketActivityEvent).where(
            TicketActivityEvent.ticket_id == ticket.id
        ))
        payload = TicketActivityEventRead.model_validate(event).model_dump(mode="json")
        self.assertTrue(payload["created_at"].endswith("Z"))

    def test_deferred_scope_requires_reason_and_does_not_block_done(self) -> None:
        ticket = create_ticket(
            TicketCreate(
                title="Defer optional scope",
                acceptance_criteria=[{"text": "Optional export", "sort_order": 1}],
                subtasks=[{"title": "Build exporter", "sort_order": 1}],
            ),
            self.db,
        )
        criterion = self.db.scalar(select(AcceptanceCriterion).where(
            AcceptanceCriterion.ticket_id == ticket.id
        ))
        subtask = self.db.scalar(select(Subtask).where(Subtask.ticket_id == ticket.id))

        with self.assertRaises(Exception):
            save_ticket_drawer_session(
                ticket.id,
                DrawerSessionCommit(
                    ticket=DrawerTicketDraft(
                        title=ticket.title,
                        description=None,
                        priority="medium",
                        ticket_type="task",
                        status="done",
                        project_id=None,
                    ),
                    acceptance_criteria=[
                        DrawerCriterionDraft(
                            id=criterion.id,
                            text=criterion.text,
                            deferred=True,
                        )
                    ],
                    subtasks=[
                        DrawerSubtaskDraft(
                            id=subtask.id,
                            title=subtask.title,
                            status="deferred",
                        )
                    ],
                ),
                self.db,
            )
        self.db.rollback()

        result = save_ticket_drawer_session(
            ticket.id,
            DrawerSessionCommit(
                ticket=DrawerTicketDraft(
                    title=ticket.title,
                    description=None,
                    priority="medium",
                    ticket_type="task",
                    status="done",
                    project_id=None,
                ),
                acceptance_criteria=[
                    DrawerCriterionDraft(
                        id=criterion.id,
                        text=criterion.text,
                        deferred=True,
                    )
                ],
                subtasks=[
                    DrawerSubtaskDraft(
                        id=subtask.id,
                        title=subtask.title,
                        status="deferred",
                    )
                ],
                note="Moved to a later project.",
            ),
            self.db,
        )

        self.assertEqual(result.ticket.status.value, "done")
        self.assertTrue(result.acceptance_criteria[0].deferred)
        self.assertFalse(result.acceptance_criteria[0].completed)
        self.assertEqual(
            result.acceptance_criteria[0].deferred_reason,
            "Moved to a later project.",
        )
        self.assertEqual(result.subtasks[0].status.value, "deferred")
        event = self.db.scalar(select(TicketActivityEvent).where(
            TicketActivityEvent.event_type == "drawer_session_committed"
        ).order_by(TicketActivityEvent.id.desc()))
        self.assertEqual(event.note, "Moved to a later project.")
        self.assertTrue(event.new_value["acceptance_criteria"][0]["deferred"])


if __name__ == "__main__":
    unittest.main()
