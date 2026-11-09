"""Record each atomic application of approved Project Review proposals."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime


class ProjectReviewApplication(Base):
    __tablename__ = "project_review_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("project_review_attempts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    applied_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    proposal_indexes: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    resulting_changes: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now, nullable=False)
