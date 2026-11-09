"""Record immutable Project lifecycle and reporting-classification events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class ProjectLifecycleEvent(Base):
    """Preserve who archived or restored a Project without storing work content."""

    __tablename__ = "project_lifecycle_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    archive_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archive_reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_life_context: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_life_context: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )


@event.listens_for(ProjectLifecycleEvent, "before_update")
@event.listens_for(ProjectLifecycleEvent, "before_delete")
def prevent_project_lifecycle_event_mutation(*_args: object) -> None:
    """Keep Project lifecycle history append-only."""
    raise ValueError("Project lifecycle events are append-only and immutable.")
