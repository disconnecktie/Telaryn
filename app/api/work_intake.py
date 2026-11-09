"""Queue and recover advisory Work Intake operations without mutating work."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.core.time import utc_now
from app.db.session import get_db
from app.models.work_intake_attempt import (
    WorkIntakeAttempt,
    WorkIntakeAttemptStatus,
)
from app.schemas.work_intake import WorkIntakeClarificationRequest, WorkIntakeRequest
from app.schemas.work_intake_attempt import WorkIntakeAttemptRead
from app.services.auth import AuthContext, require_auth_context
from app.services.work_intake import WorkIntakeService
from app.services.workspaces import request_workspace


router = APIRouter(prefix="/work-intake", tags=["Work Intake"])


def _owned_attempt(
    db: Session,
    *,
    attempt_id: int,
    workspace_id: int,
    user_id: int,
) -> WorkIntakeAttempt:
    attempt = db.scalar(
        select(WorkIntakeAttempt).where(
            WorkIntakeAttempt.id == attempt_id,
            WorkIntakeAttempt.workspace_id == workspace_id,
            WorkIntakeAttempt.requested_by_user_id == user_id,
        )
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Work Intake operation not found.")
    return attempt


@router.post(
    "/proposals",
    response_model=WorkIntakeAttemptRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def propose_work_intake(
    request: WorkIntakeRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    provider: AIProvider = Depends(get_ai_provider),
):
    """Persist an authorized snapshot and immediately queue provider work."""
    workspace = request_workspace(db, auth)
    return WorkIntakeService(provider).queue_attempt(
        workspace_id=workspace.id,
        user_id=auth.user.id,
        source_text=request.source_text,
        db=db,
    )


@router.get("/proposals/current", response_model=WorkIntakeAttemptRead | None)
def get_current_work_intake(
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Recover this user's latest undismissed operation in the active workspace."""
    workspace = request_workspace(db, auth)
    return db.scalar(
        select(WorkIntakeAttempt)
        .where(
            WorkIntakeAttempt.workspace_id == workspace.id,
            WorkIntakeAttempt.requested_by_user_id == auth.user.id,
            WorkIntakeAttempt.dismissed_at.is_(None),
        )
        .order_by(WorkIntakeAttempt.created_at.desc(), WorkIntakeAttempt.id.desc())
    )


@router.get("/proposals/{attempt_id}", response_model=WorkIntakeAttemptRead)
def get_work_intake(
    attempt_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    return _owned_attempt(
        db,
        attempt_id=attempt_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )


@router.post(
    "/proposals/{attempt_id}/refine",
    response_model=WorkIntakeAttemptRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def refine_work_intake(
    attempt_id: int,
    request: WorkIntakeClarificationRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
    provider: AIProvider = Depends(get_ai_provider),
):
    """Queue the single allowed refinement for an owned active proposal."""
    workspace = request_workspace(db, auth)
    attempt = _owned_attempt(
        db,
        attempt_id=attempt_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    try:
        return WorkIntakeService(provider).refine_attempt(
            attempt, answers=request.answers, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/proposals/{attempt_id}/cancel", response_model=WorkIntakeAttemptRead)
def cancel_work_intake(
    attempt_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Cancel queued work or discard a running provider result when it returns."""
    workspace = request_workspace(db, auth)
    attempt = _owned_attempt(
        db,
        attempt_id=attempt_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    if attempt.status in {
        WorkIntakeAttemptStatus.PENDING,
        WorkIntakeAttemptStatus.RUNNING,
    }:
        attempt.status = WorkIntakeAttemptStatus.CANCELLED
        attempt.safe_error_category = "cancelled"
        attempt.completed_at = utc_now()
        db.commit()
        db.refresh(attempt)
    return attempt


@router.post(
    "/proposals/{attempt_id}/dismiss",
    status_code=status.HTTP_204_NO_CONTENT,
)
def dismiss_work_intake(
    attempt_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Stop recovering an operation after the user discards or continues it."""
    workspace = request_workspace(db, auth)
    attempt = _owned_attempt(
        db,
        attempt_id=attempt_id,
        workspace_id=workspace.id,
        user_id=auth.user.id,
    )
    if attempt.status in {
        WorkIntakeAttemptStatus.PENDING,
        WorkIntakeAttemptStatus.RUNNING,
    }:
        attempt.status = WorkIntakeAttemptStatus.CANCELLED
        attempt.safe_error_category = "cancelled"
        attempt.completed_at = utc_now()
    attempt.dismissed_at = utc_now()
    attempt.source_text = ""
    attempt.snapshot = {}
    attempt.result = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
