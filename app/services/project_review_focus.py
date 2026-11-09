"""Apply and reverse Current Focus recommendations outside authoritative batches."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.project_review import ProjectReviewProposalType, ProjectReviewResult
from app.core.time import utc_now
from app.models.project_review_proposal_decision import (
    ProjectReviewProposalDecision,
    ProjectReviewProposalDecisionValue,
)
from app.models.ticket import Ticket
from app.services.focus import clear_all_current_focus, focus_ticket


def _proposal(attempt, proposal_index):
    proposals = ProjectReviewResult.model_validate(attempt.result).proposals
    if proposal_index < 0 or proposal_index >= len(proposals):
        raise HTTPException(status_code=404, detail="Project Review proposal not found")
    proposal = proposals[proposal_index]
    if proposal.proposal_type != ProjectReviewProposalType.RECOMMEND_CURRENT_FOCUS:
        raise HTTPException(status_code=422, detail="This proposal is not a Current Focus recommendation.")
    return proposal


def make_recommended_focus(db: Session, *, attempt, proposal_index, workspace_id, user_id):
    proposal = _proposal(attempt, proposal_index)
    target = db.scalar(select(Ticket).where(
        Ticket.id == proposal.target_ticket_id,
        Ticket.workspace_id == workspace_id,
        Ticket.project_id == attempt.project_id,
    ))
    if target is None:
        raise HTTPException(status_code=409, detail="The recommended Ticket is no longer available.")

    previous_ticket_id = focus_ticket(
        db,
        ticket=target,
        workspace_id=workspace_id,
        user_id=user_id,
    )

    decision = db.scalar(select(ProjectReviewProposalDecision).where(
        ProjectReviewProposalDecision.review_attempt_id == attempt.id,
        ProjectReviewProposalDecision.proposal_index == proposal_index,
    ))
    if decision is None:
        decision = ProjectReviewProposalDecision(
            review_attempt_id=attempt.id, workspace_id=workspace_id,
            project_id=attempt.project_id, decided_by_user_id=user_id,
            proposal_index=proposal_index,
            decision=ProjectReviewProposalDecisionValue.APPROVED,
        )
        db.add(decision)
    if decision.application_id is not None:
        raise HTTPException(status_code=409, detail="This proposal was already applied authoritatively.")
    decision.decision = ProjectReviewProposalDecisionValue.APPROVED
    decision.focus_previous_ticket_id = previous_ticket_id
    decision.focus_applied_at = utc_now()
    db.commit()
    db.refresh(decision)
    return decision


def undo_recommended_focus(db: Session, *, attempt, proposal_index, workspace_id, user_id):
    _proposal(attempt, proposal_index)
    decision = db.scalar(select(ProjectReviewProposalDecision).where(
        ProjectReviewProposalDecision.review_attempt_id == attempt.id,
        ProjectReviewProposalDecision.proposal_index == proposal_index,
        ProjectReviewProposalDecision.decided_by_user_id == user_id,
    ))
    if decision is None or decision.focus_applied_at is None:
        raise HTTPException(status_code=409, detail="This Focus recommendation has not been applied.")

    clear_all_current_focus(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
    )
    if decision.focus_previous_ticket_id is not None:
        previous_ticket = db.scalar(
            select(Ticket).where(
                Ticket.id == decision.focus_previous_ticket_id,
                Ticket.workspace_id == workspace_id,
            )
        )
        if previous_ticket is not None:
            try:
                focus_ticket(
                    db,
                    ticket=previous_ticket,
                    workspace_id=workspace_id,
                    user_id=user_id,
                )
            except HTTPException:
                # Undo restores only a previous focus that remains eligible and
                # available; later workflow choices are never silently reversed.
                pass

    decision.focus_applied_at = None
    decision.focus_previous_ticket_id = None
    db.commit()
    db.refresh(decision)
    return decision
