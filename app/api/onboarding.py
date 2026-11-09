"""Expose first-run progress without creating or changing user work."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import get_db
from app.models.onboarding_state import OnboardingState
from app.schemas.onboarding import OnboardingProgress, OnboardingVisibilityUpdate
from app.services.auth import AuthContext, require_auth_context
from app.services.onboarding import onboarding_progress

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


@router.get("/", response_model=OnboardingProgress)
def read_onboarding(db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context)):
    return onboarding_progress(db, user_id=auth.user.id, workspace_id=auth.workspace.id)


@router.patch("/", response_model=OnboardingProgress)
def update_onboarding(payload: OnboardingVisibilityUpdate, db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context)):
    state = db.scalar(select(OnboardingState).where(
        OnboardingState.user_id == auth.user.id,
        OnboardingState.workspace_id == auth.workspace.id,
    ))
    if state is None:
        state = OnboardingState(user_id=auth.user.id, workspace_id=auth.workspace.id)
        db.add(state)
    state.dismissed_at = utc_now() if payload.dismissed else None
    db.commit()
    return onboarding_progress(db, user_id=auth.user.id, workspace_id=auth.workspace.id)
