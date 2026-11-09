"""Define the private workspace boundary that contains Telaryn work records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class Workspace(Base):
    """A private container for projects and tickets, ready for future collaboration."""

    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Allocation sources for workspace-local, human-facing work numbers.
    next_project_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    next_ticket_number: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False)

    created_by: Mapped["User"] = relationship("User", back_populates="created_workspaces")
    memberships: Mapped[list["WorkspaceMembership"]] = relationship("WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="workspace")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="workspace")

