"""Expose local login, session inspection, and immediate logout invalidation."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import AuthenticatedUserRead, LoginRequest
from app.services.auth import (
    AuthContext,
    authenticate_user,
    create_auth_session,
    require_auth_context,
    utcnow,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def identity_response(context: AuthContext) -> AuthenticatedUserRead:
    return AuthenticatedUserRead(
        id=context.user.id,
        email=context.user.email,
        display_name=context.user.display_name,
        workspace_id=context.workspace.id,
        workspace_name=context.workspace.name,
    )


@router.post("/login", response_model=AuthenticatedUserRead)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    membership = user.workspace_memberships[0] if user.workspace_memberships else None
    if membership is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    session, raw_token = create_auth_session(db, user, workspace_id=membership.workspace_id)
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_lifetime_days * 86400,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    return identity_response(AuthContext(user=user, workspace=membership.workspace, session=session))


@router.get("/session", response_model=AuthenticatedUserRead)
def current_session(context: AuthContext = Depends(require_auth_context)):
    return identity_response(context)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    context: AuthContext = Depends(require_auth_context),
    db: Session = Depends(get_db),
):
    context.session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
