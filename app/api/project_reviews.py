"""Expose Project Review generation, decisions, reversible focus, and atomic application."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.db.session import get_db
from app.models.project_review_attempt import ProjectReviewAttempt
from app.schemas.project_review_attempt import ProjectReviewAttemptRead
from app.schemas.project_review_application import (
    ProjectReviewApplicationPreview,
    ProjectReviewApplicationRead,
)
from app.schemas.project_review_proposal_decision import (
    ProjectReviewProposalDecisionRead,
    ProjectReviewProposalDecisionWrite,
)
from app.services.ai_context_policy import require_project_ai_context
from app.services.auth import AuthContext, require_auth_context
from app.services.project_review_applications import (
    apply_approved_proposals,
    preview_application,
)
from app.services.project_review_proposal_decisions import (
    list_proposal_decisions,
    require_current_review,
    require_owned_review,
    save_proposal_decision,
)
from app.services.project_review_focus import (
    make_recommended_focus,
    undo_recommended_focus,
)
from app.services.project_review_observability import (
    log_project_review_event,
    new_project_review_reference,
    safe_failure_location,
)
from app.services.project_reviews import ProjectReviewService
from app.services.workspaces import (
    activity_actor,
    request_workspace,
    require_active_project,
    require_workspace_project,
)


router = APIRouter(prefix="/projects/{project_id}/reviews", tags=["Project Reviews"])


def _unexpected_review_error(
    error: Exception,
    *,
    operation: str,
    reference_id: str,
    project_id: int,
    workspace_id: int | None = None,
    requester_id: int | None = None,
) -> HTTPException:
    """Convert an unexpected failure into a safe response and correlated log."""
    log_project_review_event(
        "unexpected_failure",
        reference_id=reference_id,
        project_id=project_id,
        workspace_id=workspace_id,
        requester_id=requester_id,
        safe_category=operation,
        exception_type=type(error).__name__,
        failure_location=safe_failure_location(error),
        level=logging.ERROR,
    )
    return HTTPException(
        status_code=500,
        detail=(
            "Telaryn could not complete the Project Review request. "
            "No Project or Ticket data was changed. "
            f"Reference: {reference_id}"
        ),
    )


@router.post(
    "/",
    response_model=ProjectReviewAttemptRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_project_review(
    project_id: int,
    force_fresh: bool = Query(
        default=False,
        description="Queue a new review even when an unchanged snapshot has a completed review.",
    ),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    provider: AIProvider = Depends(get_ai_provider),
):
    reference_id = new_project_review_reference()
    workspace_id = None
    try:
        workspace = request_workspace(db, auth)
        workspace_id = workspace.id
        project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
        require_active_project(project)
        require_project_ai_context(project)
        log_project_review_event(
            "requested",
            reference_id=reference_id,
            project_id=project_id,
            workspace_id=workspace.id,
            requester_id=auth.user.id,
            provider=provider.name,
            model=provider.model_name,
        )
        return ProjectReviewService(provider).review_project(
            project,
            workspace_id=workspace.id,
            user_id=auth.user.id,
            db=db,
            reference_id=reference_id,
            force_fresh=force_fresh,
        )
    except HTTPException:
        raise
    except Exception as error:
        raise _unexpected_review_error(
            error,
            operation="create",
            reference_id=reference_id,
            project_id=project_id,
            workspace_id=workspace_id,
            requester_id=auth.user.id,
        ) from error


@router.get("/", response_model=list[ProjectReviewAttemptRead])
def list_project_reviews(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    reference_id = new_project_review_reference()
    workspace_id = None
    try:
        workspace = request_workspace(db, auth)
        workspace_id = workspace.id
        require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
        return db.scalars(
            select(ProjectReviewAttempt)
            .where(
                ProjectReviewAttempt.workspace_id == workspace.id,
                ProjectReviewAttempt.project_id == project_id,
                ProjectReviewAttempt.requested_by_user_id == auth.user.id,
            )
            .order_by(ProjectReviewAttempt.created_at.desc(), ProjectReviewAttempt.id.desc())
        ).all()
    except HTTPException:
        raise
    except Exception as error:
        raise _unexpected_review_error(
            error,
            operation="list",
            reference_id=reference_id,
            project_id=project_id,
            workspace_id=workspace_id,
            requester_id=auth.user.id,
        ) from error


@router.get("/{review_id}", response_model=ProjectReviewAttemptRead)
def get_project_review(
    project_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    reference_id = new_project_review_reference()
    workspace_id = None
    try:
        workspace = request_workspace(db, auth)
        workspace_id = workspace.id
        require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
        attempt = db.scalar(
            select(ProjectReviewAttempt).where(
                ProjectReviewAttempt.id == review_id,
                ProjectReviewAttempt.workspace_id == workspace.id,
                ProjectReviewAttempt.project_id == project_id,
                ProjectReviewAttempt.requested_by_user_id == auth.user.id,
            )
        )
        if attempt is None:
            raise HTTPException(status_code=404, detail="Project Review not found")
        return attempt
    except HTTPException:
        raise
    except Exception as error:
        raise _unexpected_review_error(
            error,
            operation="get",
            reference_id=reference_id,
            project_id=project_id,
            workspace_id=workspace_id,
            requester_id=auth.user.id,
        ) from error


@router.get(
    "/{review_id}/decisions",
    response_model=list[ProjectReviewProposalDecisionRead],
)
def get_project_review_proposal_decisions(
    project_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Return only this user's decisions for proposals in one immutable review."""
    workspace = request_workspace(db, auth)
    require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    attempt = require_owned_review(
        db,
        review_id=review_id,
        project_id=project_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    return list_proposal_decisions(db, attempt=attempt)


@router.put(
    "/{review_id}/proposals/{proposal_index}/decision",
    response_model=ProjectReviewProposalDecisionRead,
)
def put_project_review_proposal_decision(
    project_id: int,
    review_id: int,
    proposal_index: int,
    payload: ProjectReviewProposalDecisionWrite,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Persist a reversible decision without applying any Project or Ticket change."""
    workspace = request_workspace(db, auth)
    project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    require_active_project(project)
    attempt = require_owned_review(
        db,
        review_id=review_id,
        project_id=project_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    require_current_review(
        db,
        attempt=attempt,
        project=project,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    return save_proposal_decision(
        db,
        attempt=attempt,
        proposal_index=proposal_index,
        payload=payload,
        workspace_id=workspace.id,
        project_id=project_id,
        user_id=auth.user.id,
    )


@router.get(
    "/{review_id}/application-preview",
    response_model=ProjectReviewApplicationPreview,
)
def get_project_review_application_preview(
    project_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Show the exact approved candidates without applying them."""
    workspace = request_workspace(db, auth)
    project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    attempt = require_owned_review(
        db, review_id=review_id, project_id=project_id,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    require_current_review(
        db, attempt=attempt, project=project,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    return preview_application(db, attempt=attempt)


@router.post(
    "/{review_id}/apply",
    response_model=ProjectReviewApplicationRead,
)
def apply_project_review_proposals(
    project_id: int,
    review_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Commit all approved candidates together or roll the entire batch back."""
    workspace = request_workspace(db, auth)
    project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    require_active_project(project)
    attempt = require_owned_review(
        db, review_id=review_id, project_id=project_id,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    require_current_review(
        db, attempt=attempt, project=project,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    actor_type, actor_id = activity_actor(auth)
    try:
        return apply_approved_proposals(
            db, attempt=attempt, project=project,
            workspace_id=workspace.id, user_id=auth.user.id,
            actor_type=actor_type, actor_id=actor_id,
        )
    except Exception:
        db.rollback()
        raise


@router.post(
    "/{review_id}/proposals/{proposal_index}/make-focus",
    response_model=ProjectReviewProposalDecisionRead,
)
def make_project_review_recommendation_focus(
    project_id: int,
    review_id: int,
    proposal_index: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Act on focus advice separately from authoritative Project/Ticket application."""
    workspace = request_workspace(db, auth)
    project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    require_active_project(project)
    attempt = require_owned_review(
        db, review_id=review_id, project_id=project_id,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    require_current_review(
        db, attempt=attempt, project=project,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    return make_recommended_focus(
        db, attempt=attempt, proposal_index=proposal_index,
        workspace_id=workspace.id, user_id=auth.user.id,
    )


@router.post(
    "/{review_id}/proposals/{proposal_index}/undo-focus",
    response_model=ProjectReviewProposalDecisionRead,
)
def undo_project_review_recommendation_focus(
    project_id: int,
    review_id: int,
    proposal_index: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Restore the prior Current Focus while that explicit reversal remains available."""
    workspace = request_workspace(db, auth)
    require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    project = require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    require_active_project(project)
    attempt = require_owned_review(
        db, review_id=review_id, project_id=project_id,
        workspace_id=workspace.id, user_id=auth.user.id,
    )
    return undo_recommended_focus(
        db, attempt=attempt, proposal_index=proposal_index,
        workspace_id=workspace.id, user_id=auth.user.id,
    )

