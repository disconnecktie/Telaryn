"""Record immutable, metadata-only changes to a Project's AI-context policy."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class ProjectAIPolicyEvent(Base):
    """An append-only audit event that never stores Project or Ticket content."""

    __tablename__ = "project_ai_policy_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"),
        index=True,
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    actor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
        nullable=False,
    )
    previous_ai_context_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_ai_context_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )


@event.listens_for(ProjectAIPolicyEvent, "before_update")
@event.listens_for(ProjectAIPolicyEvent, "before_delete")
def prevent_project_ai_policy_event_mutation(*_args: object) -> None:
    """Keep policy history append-only once it has been recorded."""
    raise ValueError("Project AI policy events are append-only and immutable.")
