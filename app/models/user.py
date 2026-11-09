"""Persist Telaryn identities independently from workspace-owned work."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class User(Base):
    """An Telaryn identity with an optional locally managed password credential."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("account_status IN ('active', 'disabled')", name="ck_user_account_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(500), nullable=True)
    account_status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )

    created_workspaces: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="created_by"
    )
    workspace_memberships: Mapped[list["WorkspaceMembership"]] = relationship(
        "WorkspaceMembership", back_populates="user", cascade="all, delete-orphan"
    )
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )

