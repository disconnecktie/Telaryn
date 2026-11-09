"""Verify Project Review application is exact, atomic, and auditable."""

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.models.project import Project
from app.models.project_review_attempt import ProjectReviewAttempt, ProjectReviewAttemptStatus
from app.models.project_review_proposal_decision import ProjectReviewProposalDecision, ProjectReviewProposalDecisionValue
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_activity_event import TicketActivityEvent
from app.services.project_review_applications import apply_approved_proposals, preview_application
from app.services.workspaces import get_or_create_bootstrap_workspace


EMPTY = {
    "title": None, "description": None, "priority": None, "ticket_type": None,
    "acceptance_criteria": [], "subtasks": [], "project_description": None,
    "project_purpose": None, "project_why_it_matters": None, "project_target_date": None,
}


class ProjectReviewApplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.workspace = get_or_create_bootstrap_workspace(self.db)
        self.project = Project(workspace_id=self.workspace.id, name="House Projects")
        self.db.add(self.project); self.db.flush()
        self.ticket = Ticket(
            workspace_id=self.workspace.id, project_id=self.project.id, title="Build fence"
        )
        self.db.add(self.ticket); self.db.flush()
        proposal = {
            "proposal_type": "add_acceptance_criteria",
            "summary": "Define dog containment outcome.",
            "basis": "supported", "significance": "necessary",
            "evidence": [{"source_type": "ticket", "source_id": self.ticket.id,
                          "field_name": "title", "summary": "Fence ticket"}],
            "target_project_id": None, "target_ticket_id": self.ticket.id,
            "proposed_changes": {**EMPTY, "acceptance_criteria": ["Dogs remain safely contained"]},
        }
        self.attempt = ProjectReviewAttempt(
            workspace_id=self.workspace.id, project_id=self.project.id,
            requested_by_user_id=self.workspace.created_by_user_id,
            snapshot_version="a" * 64, successful_snapshot_key="a" * 64,
            status=ProjectReviewAttemptStatus.COMPLETED, provider="fake", model="fake",
            result={"outcome": "changes_proposed", "summary": "Add definition of done.",
                    "findings": [], "risks": [], "planning_guidance": [],
                    "proposals": [proposal], "recommended_focus": None},
        )
        self.db.add(self.attempt); self.db.flush()
        self.decision = ProjectReviewProposalDecision(
            review_attempt_id=self.attempt.id, workspace_id=self.workspace.id,
            project_id=self.project.id,
            decided_by_user_id=self.workspace.created_by_user_id,
            proposal_index=0, decision=ProjectReviewProposalDecisionValue.APPROVED,
        )
        self.db.add(self.decision); self.db.commit()

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_applies_approved_candidate_and_records_provenance(self):
        original_status = self.ticket.status
        application = apply_approved_proposals(
            self.db, attempt=self.attempt, project=self.project,
            workspace_id=self.workspace.id,
            user_id=self.workspace.created_by_user_id,
            actor_type="user", actor_id=str(self.workspace.created_by_user_id),
        )
        self.db.refresh(self.ticket); self.db.refresh(self.decision)

        self.assertEqual([item.text for item in self.ticket.acceptance_criteria],
                         ["Dogs remain safely contained"])
        self.assertEqual(self.ticket.status, original_status)
        self.assertEqual(original_status, TicketStatus.READY)
        self.assertEqual(self.decision.application_id, application.id)
        activity = self.db.scalar(select(TicketActivityEvent))
        self.assertEqual(activity.event_type, "project_review_applied")
        self.assertEqual(activity.new_value["application_id"], application.id)

    def test_duplicate_rejects_before_any_authoritative_mutation(self):
        from app.models.acceptance_criterion import AcceptanceCriterion
        self.db.add(AcceptanceCriterion(
            ticket_id=self.ticket.id, text="Dogs remain safely contained"
        ))
        self.db.commit()
        with self.assertRaises(Exception):
            apply_approved_proposals(
                self.db, attempt=self.attempt, project=self.project,
                workspace_id=self.workspace.id,
                user_id=self.workspace.created_by_user_id,
                actor_type="user", actor_id=str(self.workspace.created_by_user_id),
            )
        self.assertIsNone(self.decision.application_id)
        self.assertIsNone(self.db.scalar(select(TicketActivityEvent)))

    def test_preview_contains_exact_approved_candidate(self):
        preview = preview_application(self.db, attempt=self.attempt)
        self.assertTrue(preview.can_apply)
        self.assertEqual(preview.items[0].candidate_changes["acceptance_criteria"],
                         ["Dogs remain safely contained"])


if __name__ == "__main__":
    unittest.main()
