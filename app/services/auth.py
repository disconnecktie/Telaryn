"""Own password hashing, opaque sessions, and authenticated workspace resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import secrets

from fastapi import Cookie, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership


password_hash = PasswordHash.recommended()


def utcnow() -> datetime:
    """Return aware UTC for compatibility with existing authentication callers."""
    return utc_now()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    return bool(encoded) and password_hash.verify(password, encoded)


def digest_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthContext:
    user: User
    workspace: Workspace
    session: AuthSession


def create_auth_session(db: Session, user: User, *, workspace_id: int | None = None) -> tuple[AuthSession, str]:
    raw_token = secrets.token_urlsafe(48)
    session = AuthSession(
        user_id=user.id,
        workspace_id=workspace_id,
        token_hash=digest_session_token(raw_token),
        expires_at=utc_now() + timedelta(days=settings.session_lifetime_days),
    )
    db.add(session)
    db.flush()
    return session, raw_token


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    return user if user and user.account_status == "active" and verify_password(password, user.password_hash) else None


def require_auth_context(
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    db: Session = Depends(get_db),
) -> AuthContext:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )
    if not session_token:
        raise unauthorized
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == digest_session_token(session_token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utc_now(),
        )
    )
    if session is None or session.user.account_status != "active":
        raise unauthorized
    membership_query = select(WorkspaceMembership).where(WorkspaceMembership.user_id == session.user_id)
    if session.workspace_id is not None:
        membership_query = membership_query.where(WorkspaceMembership.workspace_id == session.workspace_id)
    membership = db.scalar(membership_query.order_by(WorkspaceMembership.id))
    if membership is None:
        raise unauthorized
    return AuthContext(user=session.user, workspace=membership.workspace, session=session)
