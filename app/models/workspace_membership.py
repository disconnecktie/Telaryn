"""Persist membership explicitly so private workspaces can later be shared safely."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class WorkspaceMembership(Base):
    """A user's role within one workspace; only owner exists in the first auth slice."""

    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="owner", nullable=False)
    default_project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="workspace_memberships")
