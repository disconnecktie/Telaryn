"""Verify bounded Project Review context, versioning, and evidence selection."""

from datetime import datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_update_entry import TicketUpdateEntry
from app.services.project_review_context import build_project_review_snapshot
from app.services.workspaces import get_or_create_bootstrap_workspace


class ProjectReviewContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.workspace = get_or_create_bootstrap_workspace(self.db)
        self.project = Project(
            workspace_id=self.workspace.id,
            name="Telaryn Development",
            purpose="Reduce cognitive burden.",
            why_it_matters="Telaryn is now useful.",
        )
        self.db.add(self.project)
        self.db.flush()
        self.active = Ticket(
            workspace_id=self.workspace.id,
            project_id=self.project.id,
            title="Build Project Review",
            description="First bounded slice.",
            status=TicketStatus.IN_PROGRESS,
        )
        self.done = Ticket(
            workspace_id=self.workspace.id,
            project_id=self.project.id,
            title="Completed foundation",
            description="Historical detail should not be copied.",
            status=TicketStatus.DONE,
        )
        self.db.add_all([self.active, self.done])
        self.db.flush()
        self.criterion = AcceptanceCriterion(
            ticket_id=self.active.id,
            text="Context is bounded",
            sort_order=1,
        )
        self.db.add_all(
            [
                self.criterion,
                AcceptanceCriterion(
                    ticket_id=self.active.id,
                    text="Later scope",
                    deferred=True,
                    deferred_reason="Not needed for the first slice",
                    sort_order=2,
                ),
                Subtask(
                    ticket_id=self.active.id,
                    title="Assemble snapshot",
                    status=SubtaskStatus.IN_PROGRESS,
                    sort_order=1,
                ),
                Subtask(
                    ticket_id=self.active.id,
                    title="Scale later",
                    status=SubtaskStatus.DEFERRED,
                    deferred_reason="Await usage evidence",
                    sort_order=2,
                ),
            ]
        )
        start = datetime(2026, 8, 28, 8, 0)
        self.db.add_all(
            [
                TicketUpdateEntry(
                    ticket_id=self.active.id,
                    content="Older evidence",
                    created_at=start,
                ),
                TicketUpdateEntry(
                    ticket_id=self.active.id,
                    content="Latest meaningful evidence",
                    created_at=start + timedelta(minutes=1),
                ),
                TicketUpdateEntry(
                    ticket_id=self.done.id,
                    content="Terminal history should not enter active context",
                    created_at=start + timedelta(minutes=2),
                ),
                MyWorkPreference(
                    user_id=self.workspace.created_by_user_id,
                    workspace_id=self.workspace.id,
                    ticket_id=self.active.id,
                    is_current_focus=True,
                    availability_mode=FocusAvailabilityMode.MANUAL,
                ),
            ]
        )
        for index in range(25):
            self.db.add(
                TicketActivityEvent(
                    ticket_id=self.active.id,
                    event_type="ticket_field_changed",
                    field_name="description",
                    note=f"Meaningful change {index}",
                    created_at=start + timedelta(minutes=index),
                )
            )
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def build_snapshot(self, now: datetime):
        return build_project_review_snapshot(
            self.project,
            workspace_id=self.workspace.id,
            user_id=self.workspace.created_by_user_id,
            db=self.db,
            now=now,
        )

    def test_builds_bounded_active_context_and_terminal_summaries(self) -> None:
        snapshot = self.build_snapshot(datetime(2026, 8, 29, 12, 0))
        active = next(item for item in snapshot.tickets if item.id == self.active.id)
        done = next(item for item in snapshot.tickets if item.id == self.done.id)

        self.assertEqual(snapshot.project.purpose, "Reduce cognitive burden.")
        self.assertEqual(snapshot.current_focus_ticket_id, self.active.id)
        self.assertEqual(active.latest_update.content, "Latest meaningful evidence")
        self.assertEqual(active.availability.mode, FocusAvailabilityMode.MANUAL)
        self.assertEqual(len(active.acceptance_criteria), 2)
        self.assertTrue(active.acceptance_criteria[1].deferred)
        self.assertEqual(len(active.subtasks), 2)
        self.assertEqual(active.subtasks[1].status, SubtaskStatus.DEFERRED)

        self.assertFalse(done.detail_included)
        self.assertIsNone(done.description)
        self.assertEqual(done.acceptance_criteria, [])
        self.assertEqual(done.subtasks, [])
        self.assertIsNone(done.latest_update)

        self.assertEqual(len(snapshot.recent_activity), 20)
        self.assertTrue(all(item.ticket_id == self.active.id for item in snapshot.recent_activity))
        self.assertEqual(snapshot.context_policy.latest_updates_per_active_ticket, 1)
        self.assertEqual(snapshot.context_policy.terminal_ticket_detail, "summary_only")

    def test_snapshot_version_is_stable_until_authoritative_context_changes(self) -> None:
        first = self.build_snapshot(datetime(2026, 8, 29, 12, 0))
        second = self.build_snapshot(datetime(2026, 8, 29, 12, 5))
        self.assertEqual(first.snapshot_version, second.snapshot_version)
        self.assertNotEqual(first.generated_at, second.generated_at)

        self.criterion.text = "Context remains intentionally bounded"
        self.criterion.updated_at = datetime(2026, 8, 29, 12, 6)
        self.db.commit()
        changed = self.build_snapshot(datetime(2026, 8, 29, 12, 7))

        self.assertNotEqual(first.snapshot_version, changed.snapshot_version)
        self.assertEqual(len(changed.snapshot_version), 64)

