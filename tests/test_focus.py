"""Verify shared Current Focus eligibility, replacement, and availability rules."""

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register the complete SQLAlchemy model graph
from app.db.base import Base
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.project import Project
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.user import User
from app.models.workspace import Workspace
from app.services.focus import focus_ticket


class CurrentFocusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.user = User(email="jay@example.com", display_name="Jay")
        self.other_user = User(email="other@example.com", display_name="Other")
        self.db.add_all([self.user, self.other_user])
        self.db.flush()
        self.workspace = Workspace(
            name="Jay's Workspace",
            created_by_user_id=self.user.id,
        )
        self.other_workspace = Workspace(
            name="Other Workspace",
            created_by_user_id=self.other_user.id,
        )
        self.db.add_all([self.workspace, self.other_workspace])
        self.db.flush()
        self.project = Project(
            name="Telaryn Development",
            workspace_id=self.workspace.id,
        )
        self.db.add(self.project)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def ticket(
        self,
        title: str,
        status: TicketStatus,
        *,
        workspace_id: int | None = None,
    ) -> Ticket:
        ticket = Ticket(
            title=title,
            status=status,
            workspace_id=workspace_id or self.workspace.id,
            project_id=self.project.id if workspace_id is None else None,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def focus(self, ticket: Ticket, *, make_available: bool = False):
        return focus_ticket(
            self.db,
            ticket=ticket,
            workspace_id=self.workspace.id,
            user_id=self.user.id,
            make_available=make_available,
        )

    def test_ready_and_in_progress_tickets_replace_focus_without_workflow_changes(self):
        ready = self.ticket("Ready work", TicketStatus.READY)
        active = self.ticket("Active work", TicketStatus.IN_PROGRESS)
        activity_before = self.db.scalar(
            select(func.count()).select_from(TicketActivityEvent)
        )

        self.assertIsNone(self.focus(ready))
        self.assertEqual(self.focus(active), ready.id)
        self.db.commit()

        focused = self.db.scalar(
            select(MyWorkPreference).where(
                MyWorkPreference.user_id == self.user.id,
                MyWorkPreference.workspace_id == self.workspace.id,
                MyWorkPreference.is_current_focus.is_(True),
            )
        )
        self.assertEqual(focused.ticket_id, active.id)
        self.assertEqual(ready.status, TicketStatus.READY)
        self.assertEqual(active.status, TicketStatus.IN_PROGRESS)
        self.assertEqual(
            self.db.scalar(select(func.count()).select_from(TicketActivityEvent)),
            activity_before,
        )

    def test_ineligible_ticket_statuses_are_rejected_without_replacing_focus(self):
        current = self.ticket("Current", TicketStatus.READY)
        self.focus(current)
        for status in (
            TicketStatus.BLOCKED,
            TicketStatus.REVIEW,
            TicketStatus.DONE,
            TicketStatus.CANCELLED,
        ):
            with self.subTest(status=status):
                candidate = self.ticket(f"{status.value} work", status)
                with self.assertRaises(HTTPException) as raised:
                    self.focus(candidate)
                self.assertEqual(raised.exception.status_code, 409)

        focused = self.db.scalar(
            select(MyWorkPreference).where(
                MyWorkPreference.is_current_focus.is_(True)
            )
        )
        self.assertEqual(focused.ticket_id, current.id)

    def test_unavailable_ticket_requires_explicit_restoration(self):
        ticket = self.ticket("Saturday work", TicketStatus.READY)
        preference = MyWorkPreference(
            user_id=self.user.id,
            workspace_id=self.workspace.id,
            ticket_id=ticket.id,
            availability_mode=FocusAvailabilityMode.DATE,
            available_on=date(2099, 1, 1),
        )
        self.db.add(preference)
        self.db.flush()

        with self.assertRaises(HTTPException) as raised:
            self.focus(ticket)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertFalse(preference.is_current_focus)
        self.assertEqual(preference.availability_mode, FocusAvailabilityMode.DATE)

        self.focus(ticket, make_available=True)
        self.assertTrue(preference.is_current_focus)
        self.assertEqual(
            preference.availability_mode,
            FocusAvailabilityMode.AVAILABLE,
        )
        self.assertIsNone(preference.available_on)

    def test_cross_workspace_ticket_is_not_focusable(self):
        private = self.ticket(
            "Private work",
            TicketStatus.READY,
            workspace_id=self.other_workspace.id,
        )

        with self.assertRaises(HTTPException) as raised:
            self.focus(private)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertIsNone(
            self.db.scalar(
                select(MyWorkPreference).where(
                    MyWorkPreference.is_current_focus.is_(True)
                )
            )
        )

