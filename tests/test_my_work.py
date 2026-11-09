"""Verify My Work focus, availability, ranking, and workspace isolation."""

import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register the complete SQLAlchemy model graph
from app.db.base import Base
from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.my_work_preference import FocusAvailabilityMode, MyWorkPreference
from app.models.project import Project
from app.models.subtask import Subtask, SubtaskStatus
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.services.my_work import build_my_work, ticket_context_updated_at


class MyWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.owner = User(email="jay@example.com", display_name="Jay")
        self.other = User(email="other@example.com", display_name="Other")
        self.db.add_all([self.owner, self.other])
        self.db.flush()
        self.workspace = Workspace(
            name="Jay's Workspace", created_by_user_id=self.owner.id
        )
        self.other_workspace = Workspace(
            name="Other", created_by_user_id=self.other.id
        )
        self.db.add_all([self.workspace, self.other_workspace])
        self.db.flush()
        self.project = Project(
            name="Telaryn Development",
            purpose="Build a useful personal execution system.",
            why_it_matters="Reduce the effort required to decide what comes next.",
            target_date=date(2026, 11, 1),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
            workspace_id=self.workspace.id,
        )
        self.db.add(self.project)
        self.db.flush()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def add_ticket(
        self,
        title: str,
        status: TicketStatus,
        *,
        priority: TicketPriority = TicketPriority.MEDIUM,
        updated_at: datetime,
        with_scope: bool = True,
    ) -> Ticket:
        ticket = Ticket(
            title=title,
            status=status,
            priority=priority,
            created_at=updated_at,
            updated_at=updated_at,
            workspace_id=self.workspace.id,
            project_id=self.project.id,
        )
        self.db.add(ticket)
        self.db.flush()
        if with_scope:
            self.db.add_all([
                AcceptanceCriterion(
                    ticket_id=ticket.id,
                    text="Definition",
                    completed=True,
                    created_at=updated_at,
                    updated_at=updated_at,
                ),
                Subtask(
                    ticket_id=ticket.id,
                    title=f"Execute {title}",
                    status=SubtaskStatus.TODO,
                    created_at=updated_at,
                    updated_at=updated_at,
                ),
            ])
            self.db.flush()
            self.db.refresh(ticket)
            ticket.updated_at = updated_at
            self.db.flush()
        return ticket

    def build(self, now: datetime):
        return build_my_work(
            self.workspace.id,
            self.owner.id,
            self.db,
            now=now,
        )

    def test_builds_one_focus_three_suggestions_and_supporting_sections(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        focused = self.add_ticket(
            "Current focus",
            TicketStatus.IN_PROGRESS,
            priority=TicketPriority.HIGH,
            updated_at=now,
        )
        self.db.add(MyWorkPreference(
            user_id=self.owner.id,
            workspace_id=self.workspace.id,
            ticket_id=focused.id,
            is_current_focus=True,
        ))
        self.add_ticket("Blocked work", TicketStatus.BLOCKED, updated_at=now)
        self.add_ticket(
            "Stalled in-progress work",
            TicketStatus.IN_PROGRESS,
            updated_at=now - timedelta(days=20),
        )
        self.add_ticket(
            "Ready next",
            TicketStatus.READY,
            priority=TicketPriority.CRITICAL,
            updated_at=now,
        )
        self.add_ticket(
            "No next action",
            TicketStatus.READY,
            updated_at=now,
            with_scope=False,
        )
        self.add_ticket("Another option", TicketStatus.READY, updated_at=now)
        self.add_ticket("Review me", TicketStatus.REVIEW, updated_at=now)
        self.add_ticket("Finished", TicketStatus.DONE, updated_at=now)
        self.db.commit()

        result = self.build(now)

        self.assertEqual(result.current_focus.title, "Current focus")
        self.assertEqual(result.current_focus.next_action.title, "Execute Current focus")
        self.assertEqual(
            result.current_focus.project_why_it_matters,
            "Reduce the effort required to decide what comes next.",
        )
        self.assertEqual(
            result.current_focus.focus_rationale,
            "Work is already underway. It is marked high priority. "
            "Remaining scope: 0 of 1 acceptance criterion and 1 of 1 subtask.",
        )
        self.assertEqual(
            [item.title for item in result.suggestions],
            ["Ready next", "No next action", "Another option"],
        )
        self.assertIn(
            "Needs a concrete next action",
            result.suggestions[1].reasons,
        )
        self.assertEqual(
            [item.title for item in result.needs_attention],
            ["Blocked work", "Stalled in-progress work"],
        )
        self.assertEqual([item.title for item in result.in_review], ["Review me"])
        self.assertEqual([item.title for item in result.recently_completed], ["Finished"])

    def test_distinct_same_project_tickets_receive_ticket_specific_rationales(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        first = self.add_ticket("First ticket", TicketStatus.READY, updated_at=now)
        second = self.add_ticket("Second ticket", TicketStatus.READY, updated_at=now - timedelta(minutes=1))
        first.description = "Deliver the first distinct outcome."
        second.description = "Deliver the second distinct outcome."
        self.db.commit()

        result = self.build(now)
        rationales = {item.title: item.focus_rationale for item in result.suggestions}
        self.assertIn("Deliver the first distinct outcome.", rationales[first.title])
        self.assertIn("Deliver the second distinct outcome.", rationales[second.title])
        self.assertNotEqual(rationales[first.title], rationales[second.title])
        self.assertNotIn(self.project.why_it_matters, rationales[first.title])

    def test_missing_next_action_has_meaningful_ticket_fallback(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        self.add_ticket("Unstructured ticket", TicketStatus.READY, updated_at=now, with_scope=False)
        self.db.commit()
        result = self.build(now)
        self.assertEqual(
            result.suggestions[0].focus_rationale,
            "The ticket is ready to begin. A concrete next action still needs to be defined.",
        )

    def test_long_ticket_context_is_bounded_without_cutting_the_final_word(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        ticket = self.add_ticket("Long context", TicketStatus.READY, updated_at=now)
        ticket.description = " ".join(["meaningful"] * 40)
        self.db.commit()

        rationale = self.build(now).suggestions[0].focus_rationale

        self.assertLessEqual(len(rationale.split("It addresses: ", 1)[1].split(" Remaining scope:", 1)[0]), 240)
        self.assertIn("meaningful…", rationale)

    def test_old_ready_ticket_remains_eligible_for_suggested_next(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        self.add_ticket(
            "Older prioritized backlog",
            TicketStatus.READY,
            updated_at=now - timedelta(days=45),
        )
        self.db.commit()

        result = self.build(now)

        self.assertEqual(
            [item.title for item in result.suggestions],
            ["Older prioritized backlog"],
        )
        self.assertEqual(result.needs_attention, [])

    def test_date_based_unavailability_moves_ticket_to_upcoming(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        fence = self.add_ticket(
            "Install backyard fence",
            TicketStatus.READY,
            priority=TicketPriority.HIGH,
            updated_at=now,
        )
        self.db.add(MyWorkPreference(
            user_id=self.owner.id,
            workspace_id=self.workspace.id,
            ticket_id=fence.id,
            availability_mode=FocusAvailabilityMode.DATE,
            available_on=date(2026, 8, 29),
        ))
        self.db.commit()

        result = self.build(now)

        self.assertEqual(result.suggestions, [])
        self.assertEqual([item.title for item in result.upcoming], ["Install backyard fence"])
        self.assertEqual(result.upcoming[0].available_on, date(2026, 8, 29))

        available = self.build(datetime(2026, 8, 29, 8, 0))
        self.assertEqual([item.title for item in available.suggestions], ["Install backyard fence"])
        self.assertEqual(available.upcoming, [])

    def test_context_change_restores_a_skipped_ticket(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        ticket = self.add_ticket("Wait for context", TicketStatus.READY, updated_at=now)
        self.db.flush()
        context_snapshot = ticket_context_updated_at(ticket)
        self.db.add(MyWorkPreference(
            user_id=self.owner.id,
            workspace_id=self.workspace.id,
            ticket_id=ticket.id,
            availability_mode=FocusAvailabilityMode.CONTEXT_CHANGE,
            context_ticket_updated_at=context_snapshot,
        ))
        self.db.commit()

        self.assertEqual(self.build(now).suggestions, [])
        ticket.subtasks[0].updated_at = context_snapshot + timedelta(minutes=1)
        self.db.commit()

        self.assertEqual(
            [item.title for item in self.build(now + timedelta(minutes=2)).suggestions],
            ["Wait for context"],
        )

    def test_excludes_tickets_and_preferences_owned_by_another_workspace(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        other_ticket = Ticket(
            title="Private other work",
            status=TicketStatus.IN_PROGRESS,
            workspace_id=self.other_workspace.id,
            updated_at=now,
        )
        self.db.add(other_ticket)
        self.db.flush()
        self.db.add(MyWorkPreference(
            user_id=self.other.id,
            workspace_id=self.other_workspace.id,
            ticket_id=other_ticket.id,
            is_current_focus=True,
        ))
        self.db.commit()

        result = self.build(now)

        self.assertIsNone(result.current_focus)
        self.assertEqual(result.suggestions, [])
        self.assertEqual(result.upcoming, [])

    def test_limits_suggestions_so_my_work_does_not_become_the_backlog(self) -> None:
        now = datetime(2026, 8, 26, 12, 0)
        for index in range(7):
            self.add_ticket(
                f"Ready {index}",
                TicketStatus.READY,
                priority=(
                    TicketPriority.HIGH
                    if index == 6
                    else TicketPriority.MEDIUM
                ),
                updated_at=now - timedelta(minutes=index),
            )
        self.db.commit()

        result = self.build(now)

        self.assertEqual(len(result.suggestions), 3)
        self.assertEqual(result.ready_later_count, 4)
        self.assertEqual(result.suggestions[0].title, "Ready 6")


if __name__ == "__main__":
    unittest.main()

