"""Manage reversible proposal decisions without applying authoritative changes."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.ai.project_review import (
    ProjectReviewProposal,
    ProjectReviewProposalType,
    ProjectReviewProposedChanges,
    ProjectReviewResult,
)
from app.models.project import Project
from app.models.project_review_attempt import ProjectReviewAttempt, ProjectReviewAttemptStatus
from app.models.project_review_proposal_decision import (
    ProjectReviewProposalDecision,
    ProjectReviewProposalDecisionValue,
)
from app.schemas.project_review_proposal_decision import (
    ProjectReviewProposalDecisionRead,
    ProjectReviewProposalDecisionWrite,
)
from app.services.project_review_context import build_project_review_snapshot


def _meaningful_fields(changes: ProjectReviewProposedChanges) -> set[str]:
    return {
        key
        for key, value in changes.model_dump(mode="json").items()
        if value is not None and value != "" and value != []
    }


def _validate_candidate(proposal: ProjectReviewProposal, changes: ProjectReviewProposedChanges) -> None:
    """Keep editing inside the already validated operation and target boundary."""
    fields = _meaningful_fields(changes)
    allowed = {
        ProjectReviewProposalType.CREATE_TICKET: {
            "title", "description", "priority", "ticket_type", "acceptance_criteria", "subtasks"
        },
        ProjectReviewProposalType.EDIT_TICKET: {"title", "description"},
        ProjectReviewProposalType.CHANGE_TICKET_PRIORITY: {"priority"},
        ProjectReviewProposalType.ADD_ACCEPTANCE_CRITERIA: {"acceptance_criteria"},
        ProjectReviewProposalType.ADD_SUBTASKS: {"subtasks"},
        ProjectReviewProposalType.UPDATE_PROJECT_CONTEXT: {
            "project_description", "project_purpose", "project_why_it_matters", "project_target_date"
        },
        ProjectReviewProposalType.RECOMMEND_CURRENT_FOCUS: set(),
    }[proposal.proposal_type]
    required_exact = {
        ProjectReviewProposalType.CHANGE_TICKET_PRIORITY: {"priority"},
        ProjectReviewProposalType.ADD_ACCEPTANCE_CRITERIA: {"acceptance_criteria"},
        ProjectReviewProposalType.ADD_SUBTASKS: {"subtasks"},
        ProjectReviewProposalType.RECOMMEND_CURRENT_FOCUS: set(),
    }
    valid = fields <= allowed
    if proposal.proposal_type == ProjectReviewProposalType.CREATE_TICKET:
        valid = valid and "title" in fields
    elif proposal.proposal_type in required_exact:
        valid = valid and fields == required_exact[proposal.proposal_type]
    else:
        valid = valid and bool(fields)
    if not valid:
        raise HTTPException(
            status_code=422,
            detail="Edited proposal fields do not match this proposal operation.",
        )


def require_owned_review(
    db: Session,
    *,
    review_id: int,
    project_id: int,
    workspace_id: int,
    user_id: int,
) -> ProjectReviewAttempt:
    attempt = db.scalar(
        select(ProjectReviewAttempt).where(
            ProjectReviewAttempt.id == review_id,
            ProjectReviewAttempt.project_id == project_id,
            ProjectReviewAttempt.workspace_id == workspace_id,
            ProjectReviewAttempt.requested_by_user_id == user_id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Project Review not found")
    if attempt.status != ProjectReviewAttemptStatus.COMPLETED or not attempt.result:
        raise HTTPException(status_code=409, detail="Only completed Project Reviews have proposals.")
    return attempt


def require_current_review(
    db: Session,
    *,
    attempt: ProjectReviewAttempt,
    project: Project,
    workspace_id: int,
    user_id: int,
) -> None:
    snapshot = build_project_review_snapshot(
        project,
        workspace_id=workspace_id,
        user_id=user_id,
        db=db,
    )
    if snapshot.snapshot_version != attempt.snapshot_version:
        raise HTTPException(
            status_code=409,
            detail="This Project Review is out of date. Review Again before making proposal decisions.",
        )


def list_proposal_decisions(
    db: Session,
    *,
    attempt: ProjectReviewAttempt,
) -> list[ProjectReviewProposalDecisionRead]:
    rows = db.scalars(
        select(ProjectReviewProposalDecision)
        .where(ProjectReviewProposalDecision.review_attempt_id == attempt.id)
        .order_by(ProjectReviewProposalDecision.proposal_index)
    ).all()
    by_index = {row.proposal_index: row for row in rows}
    proposal_count = len(ProjectReviewResult.model_validate(attempt.result).proposals)
    return [
        ProjectReviewProposalDecisionRead(
            proposal_index=index,
            decision=(by_index[index].decision.value if hasattr(by_index[index].decision, "value") else by_index[index].decision)
            if index in by_index else "pending",
            edited_changes=by_index[index].edited_changes if index in by_index else None,
            note=by_index[index].note if index in by_index else None,
            application_id=by_index[index].application_id if index in by_index else None,
            focus_applied_at=by_index[index].focus_applied_at if index in by_index else None,
            focus_previous_ticket_id=by_index[index].focus_previous_ticket_id if index in by_index else None,
            created_at=by_index[index].created_at if index in by_index else None,
            updated_at=by_index[index].updated_at if index in by_index else None,
        )
        for index in range(proposal_count)
    ]


def save_proposal_decision(
    db: Session,
    *,
    attempt: ProjectReviewAttempt,
    proposal_index: int,
    payload: ProjectReviewProposalDecisionWrite,
    workspace_id: int,
    project_id: int,
    user_id: int,
) -> ProjectReviewProposalDecisionRead:
    result = ProjectReviewResult.model_validate(attempt.result)
    if proposal_index < 0 or proposal_index >= len(result.proposals):
        raise HTTPException(status_code=404, detail="Project Review proposal not found")
    proposal = result.proposals[proposal_index]
    if payload.edited_changes is not None:
        _validate_candidate(proposal, payload.edited_changes)

    row = db.scalar(
        select(ProjectReviewProposalDecision).where(
            ProjectReviewProposalDecision.review_attempt_id == attempt.id,
            ProjectReviewProposalDecision.proposal_index == proposal_index,
        )
    )
    if row is not None and (row.application_id is not None or row.focus_applied_at is not None):
        raise HTTPException(
            status_code=409,
            detail="Applied proposals are final and cannot be changed.",
        )
    if payload.decision == "pending":
        if payload.edited_changes is not None or payload.note:
            raise HTTPException(status_code=422, detail="Pending decisions cannot retain edits or notes.")
        if row is not None:
            db.delete(row)
            db.commit()
        return ProjectReviewProposalDecisionRead(
            proposal_index=proposal_index,
            decision="pending",
            edited_changes=None,
            note=None,
            created_at=None,
            updated_at=None,
        )

    if row is None:
        row = ProjectReviewProposalDecision(
            review_attempt_id=attempt.id,
            workspace_id=workspace_id,
            project_id=project_id,
            decided_by_user_id=user_id,
            proposal_index=proposal_index,
            decision=ProjectReviewProposalDecisionValue(payload.decision),
        )
        db.add(row)
    row.decision = ProjectReviewProposalDecisionValue(payload.decision)
    row.edited_changes = (
        payload.edited_changes.model_dump(mode="json")
        if payload.edited_changes is not None
        else None
    )
    row.note = payload.note
    row.updated_at = utc_now()
    db.commit()
    db.refresh(row)
    return ProjectReviewProposalDecisionRead(
        proposal_index=row.proposal_index,
        decision=row.decision.value if hasattr(row.decision, "value") else row.decision,
        edited_changes=row.edited_changes,
        note=row.note,
        application_id=row.application_id,
        focus_applied_at=row.focus_applied_at,
        focus_previous_ticket_id=row.focus_previous_ticket_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
