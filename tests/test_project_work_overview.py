"""Verify project overview aggregation and attention rules."""

import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.tickets import create_ticket
from app.db.base import Base
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.schemas.ticket import TicketCreate
from app.services.project_work_overview import build_project_work_overview
from app.services.workspaces import get_or_create_bootstrap_workspace


class ProjectWorkOverviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        workspace = get_or_create_bootstrap_workspace(self.db)
        self.project = Project(name="Telaryn Development", workspace_id=workspace.id)
        self.db.add(self.project)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_aggregates_work_and_identifies_attention(self) -> None:
        now = datetime(2026, 8, 24, 12, 0)
        blocked = create_ticket(
            TicketCreate(title="Blocked work", project_id=self.project.id), self.db
        )
        blocked.status = TicketStatus.BLOCKED
        blocked.created_at = now - timedelta(days=20)
        blocked.updated_at = now - timedelta(days=20)
        done = create_ticket(
            TicketCreate(title="Finished work", project_id=self.project.id), self.db
        )
        done.status = TicketStatus.DONE
        self.db.add_all(
            [
                AcceptanceCriterion(ticket_id=blocked.id, text="Resolved", completed=True, created_at=now - timedelta(days=20), updated_at=now - timedelta(days=20)),
                AcceptanceCriterion(ticket_id=blocked.id, text="Later", deferred=True, created_at=now - timedelta(days=20), updated_at=now - timedelta(days=20)),
                Subtask(ticket_id=blocked.id, title="Execute", status=SubtaskStatus.TODO, created_at=now - timedelta(days=20), updated_at=now - timedelta(days=20)),
                Subtask(ticket_id=blocked.id, title="Deferred", status=SubtaskStatus.DEFERRED, created_at=now - timedelta(days=20), updated_at=now - timedelta(days=20)),
            ]
        )
        self.db.flush()
        blocked.updated_at = now - timedelta(days=20)
        self.db.commit()

        overview = build_project_work_overview(self.project.id, self.db, now=now)

        self.assertEqual(overview.tickets.total, 2)
        self.assertEqual(overview.tickets.blocked, 1)
        self.assertEqual(overview.tickets.done, 1)
        self.assertEqual(overview.acceptance_criteria.model_dump(), {
            "completed": 1, "total": 1, "deferred": 1
        })
        self.assertEqual(overview.subtasks.model_dump(), {
            "completed": 0, "total": 1, "deferred": 1
        })
        self.assertEqual(overview.attention[0].reasons, ["Blocked"])

    def test_ready_ticket_age_and_missing_scope_do_not_need_attention(self) -> None:
        now = datetime(2026, 8, 24, 12, 0)
        ticket = create_ticket(
            TicketCreate(title="Prioritized backlog", project_id=self.project.id),
            self.db,
        )
        ticket.updated_at = now - timedelta(days=45)
        self.db.commit()

        overview = build_project_work_overview(
            self.project.id,
            self.db,
            now=now,
        )

        self.assertEqual(overview.attention, [])

    def test_stalled_in_progress_ticket_needs_attention(self) -> None:
        now = datetime(2026, 8, 24, 12, 0)
        ticket = create_ticket(
            TicketCreate(title="Stalled execution", project_id=self.project.id),
            self.db,
        )
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = now - timedelta(days=20)
        self.db.commit()

        overview = build_project_work_overview(
            self.project.id,
            self.db,
            now=now,
        )

        self.assertEqual(overview.attention[0].id, ticket.id)
        self.assertEqual(
            overview.attention[0].reasons,
            ["No activity in 14+ days"],
        )


    def test_history_labels_a_completed_drawer_session_for_people(self) -> None:
        ticket = create_ticket(
            TicketCreate(title="Finished work", project_id=self.project.id), self.db
        )
        ticket.status = TicketStatus.DONE
        self.db.add(
            TicketActivityEvent(
                ticket_id=ticket.id,
                event_type="drawer_session_committed",
                previous_value={"ticket": {"status": TicketStatus.READY.value}},
                new_value={"ticket": {"status": TicketStatus.DONE.value}},
            )
        )
        self.db.commit()

        overview = build_project_work_overview(self.project.id, self.db)

        self.assertEqual(overview.recent_history[0].summary, "Ticket completed")


    def test_history_prefers_a_ticket_completion_over_drawer_commit(self) -> None:
        ticket = create_ticket(
            TicketCreate(title="Finished work", project_id=self.project.id), self.db
        )
        ticket.status = TicketStatus.DONE
        self.db.add(
            TicketStatusEvent(
                ticket_id=ticket.id,
                from_status=TicketStatus.READY.value,
                to_status=TicketStatus.DONE.value,
            )
        )
        self.db.commit()

        overview = build_project_work_overview(self.project.id, self.db)

        self.assertEqual(overview.recent_history[0].summary, "Ticket completed")

