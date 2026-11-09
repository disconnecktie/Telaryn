"""Fail-closed authorization for private feedback administration."""

from fastapi import Depends, HTTPException

from app.core.config import settings
from app.services.auth import AuthContext, require_auth_context


def require_feedback_reviewer(
    auth: AuthContext = Depends(require_auth_context),
) -> AuthContext:
    """Require explicit membership in the feedback-reviewer allowlist."""
    if auth.user.id not in settings.feedback_reviewer_ids:
        raise HTTPException(status_code=403, detail="Feedback review is unavailable.")
    return auth
