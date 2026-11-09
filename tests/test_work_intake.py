"""Verify bounded Work Intake context and untrusted target validation."""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - register the complete model graph
from app.ai.base import AIProvider, AIProviderError, AIReviewResult
from app.core.time import utc_now
from app.db.base import Base
from app.models.project import Project
from app.models.work_intake_attempt import WorkIntakeAttemptStatus
from app.models.ticket import Ticket
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.work_intake import (
    ProposedProject,
    ProposedTicket,
    ProposedTicketChanges,
    WorkIntakeProposal,
)
from app.services.work_intake import (
    WorkIntakeService,
    build_work_intake_snapshot,
    validate_work_intake_proposal,
)


def _database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_snapshot_excludes_private_archived_and_other_workspace_work():
    engine, db = _database()
    try:
        owner = User(email="owner@example.com", display_name="Owner")
        other = User(email="other@example.com", display_name="Other")
        db.add_all([owner, other])
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        other_workspace = Workspace(name="Other", created_by_user_id=other.id)
        db.add_all([workspace, other_workspace])
        db.flush()

        public_project = Project(
            name="Document intake",
            purpose="Shape source material into work.",
            workspace_id=workspace.id,
            updated_at=datetime(2026, 9, 15),
        )
        private_project = Project(
            name="Private planning",
            ai_context_enabled=False,
            workspace_id=workspace.id,
            updated_at=datetime(2026, 9, 15),
        )
        archived_project = Project(
            name="Archived planning",
            archived_at=datetime(2026, 9, 1),
            workspace_id=workspace.id,
            updated_at=datetime(2026, 9, 15),
        )
        other_project = Project(
            name="Other workspace",
            workspace_id=other_workspace.id,
            updated_at=datetime(2026, 9, 15),
        )
        db.add_all([public_project, private_project, archived_project, other_project])
        db.flush()
        db.add_all([
            Ticket(
                title="Upload a source document",
                workspace_id=workspace.id,
                project_id=public_project.id,
                updated_at=datetime(2026, 9, 15),
            ),
            Ticket(
                title="Private ticket",
                ai_context_enabled=False,
                workspace_id=workspace.id,
                project_id=public_project.id,
                updated_at=datetime(2026, 9, 15),
            ),
            Ticket(
                title="Ticket in private project",
                workspace_id=workspace.id,
                project_id=private_project.id,
                updated_at=datetime(2026, 9, 15),
            ),
            Ticket(
                title="Other ticket",
                workspace_id=other_workspace.id,
                project_id=other_project.id,
                updated_at=datetime(2026, 9, 15),
            ),
        ])
        db.commit()

        snapshot = build_work_intake_snapshot(
            db,
            workspace_id=workspace.id,
            source_text="Upload a document and shape it into work.",
        )

        assert [item.name for item in snapshot.projects] == ["Document intake"]
        assert [item.title for item in snapshot.tickets] == ["Upload a source document"]
    finally:
        db.close()
        engine.dispose()


def test_invented_existing_ticket_target_becomes_clarification():
    proposal = WorkIntakeProposal(
        action="update_ticket",
        summary="Update matching work.",
        rationale="The request overlaps existing work.",
        confidence="high",
        target_project_id=None,
        target_ticket_id=999,
        proposed_project=None,
        proposed_tickets=[],
        proposed_ticket_changes=ProposedTicketChanges(subtasks=["Add a safe intake step."]),
        questions=[],
    )
    snapshot = build_empty_snapshot()

    validated = validate_work_intake_proposal(proposal, snapshot)

    assert validated.action == "needs_clarification"
    assert validated.target_ticket_id is None
    assert validated.questions




def test_new_project_requires_at_least_one_starter_ticket():
    proposal = WorkIntakeProposal(
        action="create_project",
        summary="Create a new Project.",
        rationale="The outcome contains multiple deliverables.",
        confidence="high",
        target_project_id=None,
        target_ticket_id=None,
        proposed_project=ProposedProject(name="New capability"),
        proposed_tickets=[],
        proposed_ticket_changes=None,
        questions=[],
    )

    validated = validate_work_intake_proposal(proposal, build_empty_snapshot())

    assert validated.action == "needs_clarification"
    assert validated.questions == [
        "What should the first deliverable in this Project accomplish?"
    ]


def test_created_work_requires_criteria_and_subtasks_for_every_ticket():
    proposal = WorkIntakeProposal(
        action="create_project",
        summary="Create a new Project.",
        rationale="The outcome contains multiple deliverables.",
        confidence="high",
        target_project_id=None,
        target_ticket_id=None,
        proposed_project=ProposedProject(name="New capability"),
        proposed_tickets=[
            ProposedTicket(
                title="Define the first delivery",
                acceptance_criteria=["The outcome is measurable."],
                subtasks=[],
            )
        ],
        proposed_ticket_changes=None,
        questions=[],
    )

    validated = validate_work_intake_proposal(proposal, build_empty_snapshot())

    assert validated.action == "needs_clarification"
    assert validated.questions == [
        "What completion evidence and first steps should each proposed Ticket include?"
    ]


def build_empty_snapshot():
    from app.schemas.work_intake import WorkIntakeSnapshot

    return WorkIntakeSnapshot(source_text="Some work", projects=[], tickets=[])



class FakeWorkIntakeProvider(AIProvider):
    def __init__(self, response):
        self.response = response
        self.calls = 0

    @property
    def name(self):
        return "fake"

    @property
    def model_name(self):
        return "fake-intake-v1"

    def review_ticket(self, context):
        return AIReviewResult()

    def review_project(self, snapshot):
        raise NotImplementedError

    def propose_work_intake(self, snapshot):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def valid_intake_proposal():
    return WorkIntakeProposal(
        action="create_ticket",
        summary="Create one bounded Ticket.",
        rationale="The request describes one deliverable.",
        confidence="high",
        target_project_id=None,
        target_ticket_id=None,
        proposed_project=None,
        proposed_tickets=[
            ProposedTicket(
                title="Shape the requested work",
                acceptance_criteria=["The expected outcome is documented."],
                subtasks=["Confirm the requested outcome."],
            )
        ],
        proposed_ticket_changes=None,
        questions=[],
    )


def test_work_intake_queue_returns_before_provider_invocation():
    engine, db = _database()
    try:
        owner = User(email="async-owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        db.add(workspace)
        db.commit()
        provider = FakeWorkIntakeProvider(valid_intake_proposal())

        attempt = WorkIntakeService(provider).queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Create an onboarding checklist.",
            db=db,
        )

        assert attempt.status == WorkIntakeAttemptStatus.PENDING
        assert provider.calls == 0
        assert attempt.snapshot["source_text"] == "Create an onboarding checklist."
    finally:
        db.close()
        engine.dispose()


def test_work_intake_worker_persists_validated_result():
    engine, db = _database()
    try:
        owner = User(email="worker-owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        db.add(workspace)
        db.commit()
        provider = FakeWorkIntakeProvider(valid_intake_proposal())
        service = WorkIntakeService(provider)
        attempt = service.queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Create an onboarding checklist.",
            db=db,
        )
        attempt.status = WorkIntakeAttemptStatus.RUNNING
        attempt.started_at = utc_now()
        db.commit()

        completed = service.execute_queued_attempt(attempt, db=db)

        assert completed.status == WorkIntakeAttemptStatus.COMPLETED
        assert completed.result["summary"] == "Create one bounded Ticket."
        assert provider.calls == 1
    finally:
        db.close()
        engine.dispose()


def test_work_intake_allows_one_answered_refinement_without_mutating_work():
    engine, db = _database()
    try:
        owner = User(email="refine-owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        db.add(workspace)
        db.commit()
        proposal = valid_intake_proposal()
        proposal.questions = ["Who needs to approve the completed work?"]
        proposal.is_provisional = True
        proposal.clarification_prompt = "One answer would make this plan more specific."
        service = WorkIntakeService(FakeWorkIntakeProvider(proposal))
        attempt = service.queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Plan the onboarding work.",
            db=db,
        )
        attempt.status = WorkIntakeAttemptStatus.RUNNING
        attempt.started_at = utc_now()
        db.commit()
        completed = service.execute_queued_attempt(attempt, db=db)

        refined = service.refine_attempt(
            completed,
            answers=["The operations lead."],
            db=db,
        )

        assert refined.status == WorkIntakeAttemptStatus.PENDING
        assert refined.result["summary"] == "Create one bounded Ticket."
        assert refined.refinement_count == 1
        assert refined.clarification_answers == ["The operations lead."]
        assert db.query(Project).count() == 0
        assert db.query(Ticket).count() == 0

        refined.status = WorkIntakeAttemptStatus.RUNNING
        refined.started_at = utc_now()
        db.commit()
        final = service.execute_queued_attempt(refined, db=db)
        assert final.status == WorkIntakeAttemptStatus.COMPLETED
        assert final.result["questions"] == []
        assert final.result["is_provisional"] is False

        try:
            service.refine_attempt(final, answers=["A second answer"], db=db)
        except ValueError as error:
            assert "already been refined" in str(error)
        else:
            raise AssertionError("A second refinement should be rejected")
    finally:
        db.close()
        engine.dispose()


def test_work_intake_worker_persists_safe_provider_failure_only():
    engine, db = _database()
    try:
        owner = User(email="failed-owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        db.add(workspace)
        db.commit()
        provider = FakeWorkIntakeProvider(AIProviderError("provider detail"))
        service = WorkIntakeService(provider)
        attempt = service.queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Create an onboarding checklist.",
            db=db,
        )
        attempt.status = WorkIntakeAttemptStatus.RUNNING
        attempt.started_at = utc_now()
        db.commit()

        failed = service.execute_queued_attempt(attempt, db=db)

        assert failed.status == WorkIntakeAttemptStatus.FAILED
        assert failed.safe_error_category == "provider_error"
        assert failed.result is None
    finally:
        db.close()
        engine.dispose()



def test_new_work_intake_purges_superseded_recoverable_content():
    engine, db = _database()
    try:
        owner = User(email="purge-owner@example.com", display_name="Owner")
        db.add(owner)
        db.flush()
        workspace = Workspace(name="Owner", created_by_user_id=owner.id)
        db.add(workspace)
        db.commit()
        provider = FakeWorkIntakeProvider(valid_intake_proposal())
        service = WorkIntakeService(provider)
        first = service.queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Sensitive first request.",
            db=db,
        )

        service.queue_attempt(
            workspace_id=workspace.id,
            user_id=owner.id,
            source_text="Replacement request.",
            db=db,
        )
        db.refresh(first)

        assert first.dismissed_at is not None
        assert first.source_text == ""
        assert first.snapshot == {}
        assert first.result is None
    finally:
        db.close()
        engine.dispose()
