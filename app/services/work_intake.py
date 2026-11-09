"""Build and validate bounded, AI-eligible workspace intake context."""

from __future__ import annotations

import logging
import re
from time import monotonic

from pydantic import ValidationError
from sqlalchemy import select, update

from app.ai.base import (
    AIProvider,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderTimeoutError,
)
from app.core.diagnostics import log_diagnostic_event, safe_failure_location
from app.core.time import utc_now
from app.models.work_intake_attempt import (
    WorkIntakeAttempt,
    WorkIntakeAttemptStatus,
)
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.ticket import Ticket, TicketStatus
from app.schemas.work_intake import (
    WorkIntakeProjectCandidate,
    WorkIntakeProposal,
    WorkIntakeRead,
    WorkIntakeSnapshot,
    WorkIntakeTicketCandidate,
)


_WORD = re.compile(r"[a-z0-9]{3,}")


def _tokens(value: str | None) -> set[str]:
    return set(_WORD.findall((value or "").lower()))


def _score(source: set[str], *values: str | None) -> int:
    candidate = set().union(*(_tokens(value) for value in values))
    return len(source & candidate)


def build_work_intake_snapshot(
    db: Session, *, workspace_id: int, source_text: str
) -> WorkIntakeSnapshot:
    """Select relevant active work without exposing Private or archived context."""
    projects = db.scalars(
        select(Project).where(
            Project.workspace_id == workspace_id,
            Project.archived_at.is_(None),
            Project.ai_context_enabled.is_(True),
        ).order_by(Project.updated_at.desc(), Project.id.desc())
    ).all()
    tickets = db.scalars(
        select(Ticket).where(
            Ticket.workspace_id == workspace_id,
            Ticket.ai_context_enabled.is_(True),
            Ticket.status.notin_([TicketStatus.CANCELLED]),
        ).options(selectinload(Ticket.project))
        .order_by(Ticket.updated_at.desc(), Ticket.id.desc())
    ).all()
    tickets = [
        ticket for ticket in tickets
        if ticket.project is None or (
            ticket.project.archived_at is None and ticket.project.ai_context_enabled
        )
    ]

    source = _tokens(source_text)
    ranked_projects = sorted(
        projects,
        key=lambda item: (
            _score(source, item.name, item.description, item.purpose, item.why_it_matters),
            item.updated_at,
            item.id,
        ),
        reverse=True,
    )[:12]
    ranked_tickets = sorted(
        tickets,
        key=lambda item: (
            _score(
                source,
                item.title,
                item.description,
                item.project.name if item.project else None,
            ),
            item.updated_at,
            item.id,
        ),
        reverse=True,
    )[:20]

    return WorkIntakeSnapshot(
        source_text=source_text,
        projects=[
            WorkIntakeProjectCandidate(
                id=item.id,
                reference=f"PRJ-{item.workspace_project_number:03d}",
                name=item.name,
                description=item.description,
                purpose=item.purpose,
                why_it_matters=item.why_it_matters,
            )
            for item in ranked_projects
        ],
        tickets=[
            WorkIntakeTicketCandidate(
                id=item.id,
                reference=f"TKT-{item.workspace_ticket_number:03d}",
                title=item.title,
                description=item.description,
                status=item.status.value,
                priority=item.priority.value,
                ticket_type=item.ticket_type.value,
                project_id=item.project_id,
                project_name=item.project.name if item.project else None,
            )
            for item in ranked_tickets
        ],
    )


def validate_work_intake_proposal(
    proposal: WorkIntakeProposal, snapshot: WorkIntakeSnapshot
) -> WorkIntakeProposal:
    """Reject invented targets and keep proposed Ticket placement authorized."""
    project_ids = {item.id for item in snapshot.projects}
    ticket_ids = {item.id for item in snapshot.tickets}

    if proposal.target_project_id not in project_ids:
        proposal.target_project_id = None
    if proposal.target_ticket_id not in ticket_ids:
        proposal.target_ticket_id = None

    for ticket in proposal.proposed_tickets:
        if ticket.project_id not in project_ids:
            ticket.project_id = None

    if proposal.action in {"update_ticket", "use_existing"} and proposal.target_ticket_id is None:
        return WorkIntakeProposal(
            action="needs_clarification",
            summary="Telaryn needs clarification before connecting this to existing work.",
            rationale=(
                "The suggested existing Ticket could not be verified inside the "
                "authorized intake snapshot."
            ),
            confidence="low",
            target_project_id=None,
            target_ticket_id=None,
            proposed_project=None,
            proposed_tickets=[],
            proposed_ticket_changes=None,
            questions=["Which existing Ticket should this work be connected to?"],
            is_provisional=True,
            clarification_prompt=(
                "Telaryn could not verify the proposed existing Ticket. Answering this "
                "question will let it safely reshape the proposal."
            ),
        )

    if proposal.action == "create_ticket" and len(proposal.proposed_tickets) != 1:
        proposal.action = "needs_clarification"
        proposal.questions = proposal.questions or [
            "What single deliverable should the proposed Ticket represent?"
        ]
    if proposal.action == "create_tickets" and len(proposal.proposed_tickets) < 2:
        proposal.action = "needs_clarification"
        proposal.questions = proposal.questions or [
            "Should this be one Ticket or several distinct deliverables?"
        ]
    if proposal.action == "create_project" and proposal.proposed_project is None:
        proposal.action = "needs_clarification"
        proposal.questions = proposal.questions or [
            "What larger outcome should the proposed Project achieve?"
        ]
    elif proposal.action == "create_project" and not proposal.proposed_tickets:
        proposal.action = "needs_clarification"
        proposal.questions = proposal.questions or [
            "What should the first deliverable in this Project accomplish?"
        ]

    if proposal.action in {"create_project", "create_ticket", "create_tickets"}:
        incomplete_tickets = [
            ticket
            for ticket in proposal.proposed_tickets
            if not ticket.acceptance_criteria or not ticket.subtasks
        ]
        if incomplete_tickets:
            proposal.action = "needs_clarification"
            proposal.questions = proposal.questions or [
                "What completion evidence and first steps should each proposed Ticket include?"
            ]

    if snapshot.refinement_count >= 1:
        proposal.questions = []
        proposal.is_provisional = False
        proposal.clarification_prompt = None
    elif proposal.questions:
        proposal.is_provisional = True
        proposal.clarification_prompt = proposal.clarification_prompt or (
            "This proposal uses the context available now. Answering these questions "
            "will help Telaryn make it more specific and actionable."
        )

    return proposal



class WorkIntakeService:
    """Queue and execute advisory Work Intake operations without mutating work."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    def queue_attempt(
        self,
        *,
        workspace_id: int,
        user_id: int,
        source_text: str,
        db: Session,
    ) -> WorkIntakeAttempt:
        """Persist the authorized snapshot and return before provider work begins."""
        snapshot = build_work_intake_snapshot(
            db, workspace_id=workspace_id, source_text=source_text
        )
        now = utc_now()
        db.execute(
            update(WorkIntakeAttempt)
            .where(
                WorkIntakeAttempt.workspace_id == workspace_id,
                WorkIntakeAttempt.requested_by_user_id == user_id,
                WorkIntakeAttempt.dismissed_at.is_(None),
            )
            .values(
                dismissed_at=now,
                source_text="",
                snapshot={},
                result=None,
            )
        )
        attempt = WorkIntakeAttempt(
            workspace_id=workspace_id,
            requested_by_user_id=user_id,
            source_text=source_text,
            snapshot=snapshot.model_dump(mode="json"),
            status=WorkIntakeAttemptStatus.PENDING,
            provider=self.provider.name,
            model=self.provider.model_name,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        log_diagnostic_event(
            "ai_operation",
            operation="work_intake",
            outcome="queued",
            attempt_id=attempt.id,
            provider=attempt.provider,
            model=attempt.model,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        return attempt

    def execute_queued_attempt(
        self,
        attempt: WorkIntakeAttempt,
        *,
        db: Session,
    ) -> WorkIntakeAttempt:
        """Execute a claimed operation and persist only a validated advisory result."""
        if attempt.status != WorkIntakeAttemptStatus.RUNNING:
            return attempt
        started = monotonic()
        log_diagnostic_event(
            "ai_operation",
            operation="work_intake",
            outcome="provider_started",
            attempt_id=attempt.id,
            provider=attempt.provider,
            model=attempt.model,
            user_id=attempt.requested_by_user_id,
            workspace_id=attempt.workspace_id,
        )
        try:
            snapshot = WorkIntakeSnapshot.model_validate(attempt.snapshot)
            proposal = validate_work_intake_proposal(
                self.provider.propose_work_intake(snapshot), snapshot
            )
            result = WorkIntakeRead(
                **proposal.model_dump(),
                provider=attempt.provider,
                model=attempt.model,
                matched_projects=snapshot.projects,
                matched_tickets=snapshot.tickets,
            )
        except AIProviderTimeoutError:
            return self._finish_failure(
                attempt, WorkIntakeAttemptStatus.TIMED_OUT, "provider_timeout",
                started, db,
            )
        except (ValidationError, AIProviderInvalidResponseError):
            return self._finish_failure(
                attempt, WorkIntakeAttemptStatus.INVALID, "invalid_response",
                started, db,
            )
        except AIProviderError:
            return self._finish_failure(
                attempt, WorkIntakeAttemptStatus.FAILED, "provider_error",
                started, db,
            )
        except Exception as error:
            log_diagnostic_event(
                "ai_operation",
                level=logging.ERROR,
                operation="work_intake",
                outcome="failed",
                safe_category="unexpected_failure",
                attempt_id=attempt.id,
                exception_type=type(error).__name__,
                failure_location=safe_failure_location(error),
                user_id=attempt.requested_by_user_id,
                workspace_id=attempt.workspace_id,
            )
            return self._finish_failure(
                attempt, WorkIntakeAttemptStatus.INVALID, "unexpected_failure",
                started, db,
            )

        db.refresh(attempt)
        if (
            attempt.status == WorkIntakeAttemptStatus.CANCELLED
            or attempt.dismissed_at is not None
        ):
            return attempt

        attempt.result = result.model_dump(mode="json")
        attempt.status = WorkIntakeAttemptStatus.COMPLETED
        attempt.safe_error_category = None
        attempt.duration_ms = round((monotonic() - started) * 1000)
        attempt.completed_at = utc_now()
        db.commit()
        db.refresh(attempt)
        log_diagnostic_event(
            "ai_operation",
            operation="work_intake",
            outcome="completed",
            attempt_id=attempt.id,
            provider=attempt.provider,
            model=attempt.model,
            user_id=attempt.requested_by_user_id,
            workspace_id=attempt.workspace_id,
            duration_ms=attempt.duration_ms,
        )
        return attempt

    def refine_attempt(
        self,
        attempt: WorkIntakeAttempt,
        *,
        answers: list[str],
        db: Session,
    ) -> WorkIntakeAttempt:
        """Queue one refinement while retaining the original authorized snapshot."""
        if attempt.dismissed_at is not None:
            raise ValueError("The Capture Work proposal is no longer active.")
        if attempt.status != WorkIntakeAttemptStatus.COMPLETED or not attempt.result:
            raise ValueError("Only a completed Capture Work proposal can be refined.")
        snapshot = WorkIntakeSnapshot.model_validate(attempt.snapshot)
        if snapshot.refinement_count >= 1:
            raise ValueError("This Capture Work proposal has already been refined.")
        proposal = WorkIntakeRead.model_validate(attempt.result)
        questions = proposal.questions[:5]
        if not questions:
            raise ValueError("This Capture Work proposal has no clarification questions.")
        normalized = [value.strip()[:2000] for value in answers[: len(questions)]]
        normalized.extend([""] * (len(questions) - len(normalized)))
        if not any(normalized):
            raise ValueError("Answer at least one clarification question.")

        snapshot.clarification_questions = questions
        snapshot.clarification_answers = normalized
        snapshot.refinement_count = 1
        attempt.snapshot = snapshot.model_dump(mode="json")
        attempt.status = WorkIntakeAttemptStatus.PENDING
        attempt.provider = self.provider.name
        attempt.model = self.provider.model_name
        attempt.safe_error_category = None
        attempt.duration_ms = None
        attempt.started_at = None
        attempt.completed_at = None
        db.commit()
        db.refresh(attempt)
        log_diagnostic_event(
            "ai_operation",
            operation="work_intake_refinement",
            outcome="queued",
            attempt_id=attempt.id,
            provider=attempt.provider,
            model=attempt.model,
            user_id=attempt.requested_by_user_id,
            workspace_id=attempt.workspace_id,
        )
        return attempt

    @staticmethod
    def _finish_failure(
        attempt: WorkIntakeAttempt,
        status: WorkIntakeAttemptStatus,
        category: str,
        started: float,
        db: Session,
    ) -> WorkIntakeAttempt:
        db.refresh(attempt)
        if (
            attempt.status == WorkIntakeAttemptStatus.CANCELLED
            or attempt.dismissed_at is not None
        ):
            return attempt
        attempt.status = status
        attempt.safe_error_category = category
        attempt.duration_ms = round((monotonic() - started) * 1000)
        attempt.completed_at = utc_now()
        db.commit()
        log_diagnostic_event(
            "ai_operation",
            level=logging.WARNING,
            operation="work_intake",
            outcome="provider_failure",
            safe_category=category,
            attempt_id=attempt.id,
            provider=attempt.provider,
            model=attempt.model,
            user_id=attempt.requested_by_user_id,
            workspace_id=attempt.workspace_id,
            duration_ms=attempt.duration_ms,
        )
        return attempt
