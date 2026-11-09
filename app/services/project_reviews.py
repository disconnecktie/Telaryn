"""Generate bounded Project Reviews without mutating authoritative work."""

from datetime import datetime
import logging
from time import monotonic

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.ai.base import (
    AIProvider,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderTimeoutError,
)
from app.ai.project_review import (
    ProjectReviewBasis,
    ProjectReviewEvidenceSource,
    ProjectReviewProposalType,
    ProjectReviewOutcome,
    ProjectReviewResult,
)
from app.models.project import Project
from app.models.project_review_attempt import ProjectReviewAttempt, ProjectReviewAttemptStatus
from app.schemas.project_review import ProjectReviewSnapshotRead
from app.services.project_review_context import (
    build_project_review_snapshot,
    list_private_ticket_exclusions,
)
from app.services.project_review_observability import (
    log_project_review_event,
    new_project_review_reference,
    safe_failure_location,
)


class ProjectReviewInvalidResultError(AIProviderError):
    """Raised when a provider response violates Telaryn's bounded result contract."""

    def __init__(self, message: str, safe_category: str = "invalid_response"):
        super().__init__(message)
        self.safe_category = safe_category

class ProjectReviewSemanticValidationError(ValueError):
    """Identify a safe validation stage without retaining rejected provider content."""

    def __init__(self, message: str, safe_category: str):
        super().__init__(message)
        self.safe_category = safe_category


def _nonempty_change_fields(changes) -> set[str]:
    """Return only semantic mutations so empty provider fields cannot authorize work."""
    values = changes.model_dump()
    return {
        key
        for key, value in values.items()
        if value is not None and value != [] and value != ""
    }


def _validate_evidence(evidence, snapshot: ProjectReviewSnapshotRead) -> None:
    """Require every citation to resolve inside the exact provider-visible snapshot."""
    tickets = {ticket.id: ticket for ticket in snapshot.tickets}
    criteria = {
        criterion.id
        for ticket in snapshot.tickets
        for criterion in ticket.acceptance_criteria
    }
    subtasks = {
        subtask.id
        for ticket in snapshot.tickets
        for subtask in ticket.subtasks
    }
    latest_updates = {
        ticket.latest_update.id
        for ticket in snapshot.tickets
        if ticket.latest_update is not None
    }
    activity = {
        (item.source_type, item.source_id)
        for item in snapshot.recent_activity
    }
    attention_ticket_ids = {item.id for item in snapshot.work_overview.attention}

    valid = False
    if evidence.source_type == ProjectReviewEvidenceSource.PROJECT_FIELD:
        valid = (
            evidence.source_id == snapshot.project.id
            and evidence.field_name
            in {"name", "description", "purpose", "why_it_matters", "target_date"}
        )
    elif evidence.source_type == ProjectReviewEvidenceSource.TICKET:
        valid = evidence.source_id in tickets
    elif evidence.source_type == ProjectReviewEvidenceSource.ACCEPTANCE_CRITERION:
        valid = evidence.source_id in criteria
    elif evidence.source_type == ProjectReviewEvidenceSource.SUBTASK:
        valid = evidence.source_id in subtasks
    elif evidence.source_type == ProjectReviewEvidenceSource.TICKET_UPDATE:
        valid = (
            evidence.source_id in latest_updates
            or ("ticket_update", evidence.source_id) in activity
        )
    elif evidence.source_type == ProjectReviewEvidenceSource.ACTIVITY_EVENT:
        valid = ("activity_event", evidence.source_id) in activity
    elif evidence.source_type == ProjectReviewEvidenceSource.STATUS_EVENT:
        valid = ("status_event", evidence.source_id) in activity
    elif evidence.source_type == ProjectReviewEvidenceSource.WORK_OVERVIEW_SIGNAL:
        valid = (
            evidence.source_id == snapshot.project.id
            or evidence.source_id in attention_ticket_ids
        ) and evidence.field_name in {
            "attention",
            "tickets",
            "acceptance_criteria",
            "subtasks",
            "current_focus",
        }

    if not valid:
        raise ProjectReviewSemanticValidationError(
            "Project Review evidence does not resolve to the submitted snapshot.",
            "invalid_evidence",
        )


def _validate_result_against_snapshot(
    result: ProjectReviewResult,
    snapshot: ProjectReviewSnapshotRead,
) -> None:
    """Enforce evidence and operation rules before provider output becomes durable."""
    active_ticket_ids = {
        ticket.id for ticket in snapshot.tickets if ticket.detail_included
    }

    evidenced_items = [
        *result.findings,
        *result.risks,
        *result.planning_guidance,
        *result.proposals,
    ]
    if result.recommended_focus is not None:
        evidenced_items.append(result.recommended_focus)

    for item in evidenced_items:
        if item.basis in {ProjectReviewBasis.SUPPORTED, ProjectReviewBasis.INFERRED} and not item.evidence:
            raise ProjectReviewSemanticValidationError(
                "Supported or inferred review statements require snapshot evidence.",
                "invalid_evidence",
            )
        for evidence in item.evidence:
            _validate_evidence(evidence, snapshot)

    if (
        result.recommended_focus is not None
        and result.recommended_focus.ticket_id not in active_ticket_ids
    ):
        raise ProjectReviewSemanticValidationError(
            "The recommended Current Focus must reference active snapshot work.",
            "invalid_focus",
        )

    ticket_fields = {"title", "description", "priority", "ticket_type", "acceptance_criteria", "subtasks"}
    project_fields = {
        "project_description",
        "project_purpose",
        "project_why_it_matters",
        "project_target_date",
    }
    for proposal in result.proposals:
        fields = _nonempty_change_fields(proposal.proposed_changes)
        proposal_type = proposal.proposal_type
        target_ticket_is_active = proposal.target_ticket_id in active_ticket_ids

        if proposal_type == ProjectReviewProposalType.CREATE_TICKET:
            valid = (
                proposal.target_project_id == snapshot.project.id
                and proposal.target_ticket_id is None
                and "title" in fields
                and fields <= ticket_fields
            )
        elif proposal_type == ProjectReviewProposalType.EDIT_TICKET:
            valid = (
                proposal.target_project_id in {None, snapshot.project.id}
                and target_ticket_is_active
                and bool(fields)
                and fields <= {"title", "description"}
            )
        elif proposal_type == ProjectReviewProposalType.CHANGE_TICKET_PRIORITY:
            valid = target_ticket_is_active and fields == {"priority"}
        elif proposal_type == ProjectReviewProposalType.ADD_ACCEPTANCE_CRITERIA:
            valid = target_ticket_is_active and fields == {"acceptance_criteria"}
        elif proposal_type == ProjectReviewProposalType.ADD_SUBTASKS:
            valid = target_ticket_is_active and fields == {"subtasks"}
        elif proposal_type == ProjectReviewProposalType.UPDATE_PROJECT_CONTEXT:
            valid = (
                proposal.target_project_id == snapshot.project.id
                and proposal.target_ticket_id is None
                and bool(fields)
                and fields <= project_fields
            )
        else:
            valid = (
                proposal_type == ProjectReviewProposalType.RECOMMEND_CURRENT_FOCUS
                and target_ticket_is_active
                and not fields
            )

        if not valid:
            raise ProjectReviewSemanticValidationError(
                "Project Review proposal does not match its declared operation.",
                "invalid_proposal",
            )


class ProjectReviewService:
    """Queue and execute immutable full-snapshot Project Reviews."""

    def __init__(self, provider: AIProvider):
        self.provider = provider

    def review_project(
        self,
        project: Project,
        *,
        workspace_id: int,
        user_id: int,
        db: Session,
        reference_id: str | None = None,
        force_fresh: bool = False,
    ) -> ProjectReviewAttempt:
        """Compatibility entry point that now queues work instead of blocking."""
        return self.queue_project_review(
            project,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
            reference_id=reference_id,
            force_fresh=force_fresh,
        )

    def queue_project_review(
        self,
        project: Project,
        *,
        workspace_id: int,
        user_id: int,
        db: Session,
        reference_id: str | None = None,
        force_fresh: bool = False,
    ) -> ProjectReviewAttempt:
        """Persist an immutable authorized snapshot and return without provider work."""
        reference_id = reference_id or new_project_review_reference()
        snapshot = build_project_review_snapshot(
            project,
            workspace_id=workspace_id,
            user_id=user_id,
            db=db,
        )
        excluded_private_tickets = list_private_ticket_exclusions(
            project,
            workspace_id=workspace_id,
            db=db,
        )
        snapshot_prefix = snapshot.snapshot_version[:12]
        log_project_review_event(
            "snapshot_ready",
            reference_id=reference_id,
            project_id=project.id,
            workspace_id=workspace_id,
            requester_id=user_id,
            provider=self.provider.name,
            model=self.provider.model_name,
            snapshot_prefix=snapshot_prefix,
        )
        completed = db.scalar(
            select(ProjectReviewAttempt)
            .where(
                ProjectReviewAttempt.workspace_id == workspace_id,
                ProjectReviewAttempt.project_id == project.id,
                ProjectReviewAttempt.requested_by_user_id == user_id,
                ProjectReviewAttempt.successful_snapshot_key == snapshot.snapshot_version,
                ProjectReviewAttempt.status == ProjectReviewAttemptStatus.COMPLETED,
            )
            .order_by(ProjectReviewAttempt.id.desc())
        )
        if completed is not None and not force_fresh:
            log_project_review_event(
                "reused",
                reference_id=reference_id,
                attempt_id=completed.id,
                project_id=project.id,
                workspace_id=workspace_id,
                requester_id=user_id,
                provider=self.provider.name,
                model=self.provider.model_name,
                snapshot_prefix=snapshot_prefix,
            )
            return completed

        existing = db.scalar(
            select(ProjectReviewAttempt)
            .where(
                ProjectReviewAttempt.workspace_id == workspace_id,
                ProjectReviewAttempt.project_id == project.id,
                ProjectReviewAttempt.requested_by_user_id == user_id,
                ProjectReviewAttempt.snapshot_version == snapshot.snapshot_version,
                ProjectReviewAttempt.status.in_(
                    [
                        ProjectReviewAttemptStatus.PENDING,
                        ProjectReviewAttemptStatus.RUNNING,
                        ProjectReviewAttemptStatus.FAILED,
                        ProjectReviewAttemptStatus.TIMED_OUT,
                    ]
                ),
            )
            .order_by(ProjectReviewAttempt.id.desc())
        )
        if existing is not None:
            if existing.status in {
                ProjectReviewAttemptStatus.FAILED,
                ProjectReviewAttemptStatus.TIMED_OUT,
            }:
                existing.status = ProjectReviewAttemptStatus.PENDING
                existing.safe_error_category = None
                existing.duration_ms = None
                existing.started_at = None
                existing.completed_at = None
                existing.review_reference = reference_id
                db.commit()
            return existing

        attempt = ProjectReviewAttempt(
            workspace_id=workspace_id,
            project_id=project.id,
            requested_by_user_id=user_id,
            snapshot_version=snapshot.snapshot_version,
            snapshot=snapshot.model_dump(mode="json"),
            excluded_private_tickets=excluded_private_tickets or None,
            status=ProjectReviewAttemptStatus.PENDING,
            provider=self.provider.name,
            model=self.provider.model_name,
            review_reference=reference_id,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        log_project_review_event(
            "queued",
            reference_id=reference_id,
            attempt_id=attempt.id,
            project_id=project.id,
            workspace_id=workspace_id,
            requester_id=user_id,
            provider=self.provider.name,
            model=self.provider.model_name,
            snapshot_prefix=snapshot_prefix,
        )
        return attempt

    def execute_queued_review(
        self,
        attempt: ProjectReviewAttempt,
        *,
        db: Session,
    ) -> ProjectReviewAttempt:
        """Execute one claimed full snapshot outside the browser request lifecycle."""
        if attempt.status != ProjectReviewAttemptStatus.RUNNING:
            return attempt
        reference_id = attempt.review_reference or new_project_review_reference()
        started = monotonic()
        try:
            snapshot = ProjectReviewSnapshotRead.model_validate(attempt.snapshot)
            log_project_review_event(
                "provider_started",
                reference_id=reference_id,
                attempt_id=attempt.id,
                project_id=attempt.project_id,
                workspace_id=attempt.workspace_id,
                requester_id=attempt.requested_by_user_id,
                provider=self.provider.name,
                model=self.provider.model_name,
                snapshot_prefix=snapshot.snapshot_version[:12],
            )
            raw_result = self.provider.review_project(snapshot)
            result = ProjectReviewResult.model_validate(raw_result)
            _validate_result_against_snapshot(result, snapshot)
        except AIProviderTimeoutError:
            self._finish_failure(
                attempt, ProjectReviewAttemptStatus.TIMED_OUT, "provider_timeout",
                started, db,
            )
            self._log_failure(reference_id, attempt, snapshot_prefix=None)
            return attempt
        except ProjectReviewSemanticValidationError as error:
            self._finish_failure(
                attempt, ProjectReviewAttemptStatus.INVALID, error.safe_category,
                started, db,
            )
            self._log_failure(reference_id, attempt, snapshot_prefix=None)
            return attempt
        except (ValidationError, AIProviderInvalidResponseError):
            self._finish_failure(
                attempt, ProjectReviewAttemptStatus.INVALID, "invalid_schema",
                started, db,
            )
            self._log_failure(reference_id, attempt, snapshot_prefix=None)
            return attempt
        except AIProviderError:
            self._finish_failure(
                attempt, ProjectReviewAttemptStatus.FAILED, "provider_error",
                started, db,
            )
            self._log_failure(reference_id, attempt, snapshot_prefix=None)
            return attempt
        except Exception as error:
            self._finish_failure(
                attempt, ProjectReviewAttemptStatus.INVALID, "invalid_response",
                started, db,
            )
            self._log_failure(
                reference_id, attempt, snapshot_prefix=None, unexpected_error=error,
            )
            return attempt

        attempt.result = result.model_dump(mode="json")
        attempt.successful_snapshot_key = snapshot.snapshot_version
        attempt.status = ProjectReviewAttemptStatus.COMPLETED
        attempt.safe_error_category = None
        attempt.duration_ms = round((monotonic() - started) * 1000)
        attempt.completed_at = utc_now()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            winner = db.scalar(
                select(ProjectReviewAttempt).where(
                    ProjectReviewAttempt.workspace_id == attempt.workspace_id,
                    ProjectReviewAttempt.project_id == attempt.project_id,
                    ProjectReviewAttempt.requested_by_user_id
                    == attempt.requested_by_user_id,
                    ProjectReviewAttempt.successful_snapshot_key
                    == snapshot.snapshot_version,
                    ProjectReviewAttempt.status == ProjectReviewAttemptStatus.COMPLETED,
                )
            )
            duplicate = db.get(ProjectReviewAttempt, attempt.id)
            if duplicate is not None:
                duplicate.status = ProjectReviewAttemptStatus.FAILED
                duplicate.safe_error_category = "concurrent_duplicate"
                duplicate.completed_at = utc_now()
                db.commit()
            return winner or attempt

        db.refresh(attempt)
        log_project_review_event(
            "completed",
            reference_id=reference_id,
            attempt_id=attempt.id,
            project_id=attempt.project_id,
            workspace_id=attempt.workspace_id,
            requester_id=attempt.requested_by_user_id,
            provider=self.provider.name,
            model=self.provider.model_name,
            snapshot_prefix=snapshot.snapshot_version[:12],
            duration_ms=attempt.duration_ms,
        )
        return attempt

    def _log_failure(
        self,
        reference_id: str,
        attempt: ProjectReviewAttempt,
        *,
        snapshot_prefix: str | None,
        unexpected_error: Exception | None = None,
    ) -> None:
        """Emit only persisted safe failure provenance and bounded identifiers."""
        log_project_review_event(
            "failed",
            reference_id=reference_id,
            attempt_id=attempt.id,
            project_id=attempt.project_id,
            workspace_id=attempt.workspace_id,
            requester_id=attempt.requested_by_user_id,
            provider=self.provider.name,
            model=self.provider.model_name,
            snapshot_prefix=snapshot_prefix,
            duration_ms=attempt.duration_ms,
            safe_category=attempt.safe_error_category,
            exception_type=(
                type(unexpected_error).__name__ if unexpected_error is not None else None
            ),
            failure_location=(
                safe_failure_location(unexpected_error)
                if unexpected_error is not None
                else None
            ),
            level=logging.WARNING,
        )

    @staticmethod
    def _finish_failure(
        attempt: ProjectReviewAttempt,
        status: ProjectReviewAttemptStatus,
        category: str,
        started: float,
        db: Session,
    ) -> None:
        """Persist privacy-safe failure provenance without provider content."""
        attempt.status = status
        attempt.safe_error_category = category
        attempt.duration_ms = round((monotonic() - started) * 1000)
        attempt.completed_at = utc_now()
        db.commit()

