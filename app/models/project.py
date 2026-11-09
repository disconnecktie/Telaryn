"""Persist project containers and their ticket relationships."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, event, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.identifiers import generate_public_id


def generate_project_public_id() -> str:
    return generate_public_id("PRJ")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_projects_public_id"),
        UniqueConstraint(
            "workspace_id",
            "workspace_project_number",
            name="uq_projects_workspace_project_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The opaque public identifier is immutable and safe to share as a reference.
    public_id: Mapped[str] = mapped_column(
        String(18), default=generate_project_public_id, nullable=False
    )
    # Users see this familiar local number only inside the owning workspace.
    workspace_project_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Workspace is the authorization boundary; project ownership is never inferred
    # from a client-provided user identifier.
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(nullable=True)

    # Life context is explicit user-owned metadata. Telaryn never infers it.
    life_context: Mapped[str] = mapped_column(
        String(20), default="unclassified", server_default="unclassified", nullable=False
    )

    # This controls provider eligibility only. It never changes workspace access.
    ai_context_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Archival is reversible lifecycle state, never destructive deletion.
    archived_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), index=True, nullable=True
    )
    archived_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Existing archived rows remain null and are presented as Unclassified.
    archive_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    archive_reason_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def archive_report_eligible_by_default(self) -> bool:
        """Only completed archived Projects enter activity reports by default."""
        return self.archived_at is not None and self.archive_reason == "completed"

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, nullable=False
    )

    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="project")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="projects")


@event.listens_for(Project, "before_insert")
def assign_project_identifiers(_mapper, connection, project: Project) -> None:
    """Assign immutable Project references on every creation path."""
    if not project.public_id:
        project.public_id = generate_project_public_id()
    if project.workspace_project_number is not None:
        return

    from app.models.workspace import Workspace

    next_number = connection.execute(
        update(Workspace.__table__)
        .where(Workspace.id == project.workspace_id)
        .values(next_project_number=Workspace.next_project_number + 1)
        .returning(Workspace.next_project_number)
    ).scalar_one()
    project.workspace_project_number = next_number - 1

