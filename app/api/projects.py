"""Expose active Project management and reversible archival."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import get_db
from app.models.my_work_preference import MyWorkPreference
from app.models.project import Project
from app.models.project_ai_policy_event import ProjectAIPolicyEvent
from app.models.project_lifecycle_event import ProjectLifecycleEvent
from app.models.ticket import Ticket
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.project import (
    ProjectAIPolicyUpdate,
    ProjectArchiveRequest,
    ProjectCreate,
    ProjectLifecycleEventRead,
    ProjectRead,
    ProjectUpdate,
    ProjectWorkOverviewRead,
)
from app.schemas.project_review import ProjectReviewSnapshotRead
from app.services.auth import AuthContext, require_auth_context
from app.services.project_review_context import build_project_review_snapshot
from app.services.project_work_overview import build_project_work_overview
from app.services.project_export import build_project_export_snapshot, project_export_filename
from app.services.workspaces import (
    request_workspace,
    require_active_project,
    require_workspace_project,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectRead, status_code=201)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = Project(
        workspace_id=workspace.id,
        name=project_data.name,
        description=project_data.description,
        purpose=project_data.purpose,
        why_it_matters=project_data.why_it_matters,
        target_date=project_data.target_date,
        life_context=project_data.life_context,
        ai_context_enabled=project_data.ai_context_enabled,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    statement = select(Project).where(Project.workspace_id == workspace.id)
    if not include_archived:
        statement = statement.where(Project.archived_at.is_(None))
    return db.scalars(statement.order_by(Project.created_at.desc())).all()


@router.get("/public/{public_id}", response_model=ProjectRead)
def get_project_by_public_id(
    public_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Resolve a shared Project reference only inside the caller's workspace."""
    workspace = request_workspace(db, auth)
    project = db.scalar(
        select(Project).where(
            Project.public_id == public_id,
            Project.workspace_id == workspace.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    return require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)


@router.get("/{project_id}/export.json")
def export_project_json(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Download one complete Project without crossing workspace boundaries.

    This export is a user-initiated read, including archived and private work,
    not transmission to an AI provider. No mutation or external storage occurs.
    """
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    snapshot = build_project_export_snapshot(
        db, project=project, workspace_id=workspace.id
    )
    filename = project_export_filename(snapshot)
    return Response(
        content=json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{project_id}/lifecycle-events",
    response_model=list[ProjectLifecycleEventRead],
)
def list_project_lifecycle_events(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    return db.scalars(
        select(ProjectLifecycleEvent)
        .where(
            ProjectLifecycleEvent.workspace_id == workspace.id,
            ProjectLifecycleEvent.project_id == project.id,
        )
        .order_by(
            ProjectLifecycleEvent.created_at.desc(),
            ProjectLifecycleEvent.id.desc(),
        )
    ).all()


@router.post("/{project_id}/archive", response_model=ProjectRead)
def archive_project(
    project_id: int,
    archive_data: ProjectArchiveRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    if project.archived_at is not None:
        return project

    archived_at = utc_now()
    project.archived_at = archived_at
    project.archived_by_user_id = auth.user.id
    project.archive_reason = archive_data.archive_reason
    project.archive_reason_note = archive_data.archive_reason_note
    db.add(
        ProjectLifecycleEvent(
            workspace_id=workspace.id,
            project_id=project.id,
            actor_user_id=auth.user.id,
            action="archived",
            archive_reason=archive_data.archive_reason,
            archive_reason_note=archive_data.archive_reason_note,
            created_at=archived_at,
        )
    )

    db.execute(
        update(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace.id,
            WorkspaceMembership.default_project_id == project.id,
        )
        .values(default_project_id=None)
    )
    project_ticket_ids = select(Ticket.id).where(
        Ticket.workspace_id == workspace.id,
        Ticket.project_id == project.id,
    )
    db.execute(
        update(MyWorkPreference)
        .where(
            MyWorkPreference.workspace_id == workspace.id,
            MyWorkPreference.ticket_id.in_(project_ticket_ids),
        )
        .values(is_current_focus=False)
    )
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/archive-classification", response_model=ProjectRead)
def classify_archived_project(
    project_id: int,
    archive_data: ProjectArchiveRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    """Change archive metadata without restoring or unlocking Project work."""
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    if project.archived_at is None:
        raise HTTPException(
            status_code=409,
            detail="Only archived Projects can have an archive classification.",
        )
    if (
        project.archive_reason == archive_data.archive_reason
        and project.archive_reason_note == archive_data.archive_reason_note
    ):
        return project

    classified_at = utc_now()
    project.archive_reason = archive_data.archive_reason
    project.archive_reason_note = archive_data.archive_reason_note
    db.add(
        ProjectLifecycleEvent(
            workspace_id=workspace.id,
            project_id=project.id,
            actor_user_id=auth.user.id,
            action="archive_classified",
            archive_reason=archive_data.archive_reason,
            archive_reason_note=archive_data.archive_reason_note,
            created_at=classified_at,
        )
    )
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/restore", response_model=ProjectRead)
def restore_project(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    if project.archived_at is None:
        return project

    restored_at = utc_now()
    project.archived_at = None
    project.archived_by_user_id = None
    project.archive_reason = None
    project.archive_reason_note = None
    db.add(
        ProjectLifecycleEvent(
            workspace_id=workspace.id,
            project_id=project.id,
            actor_user_id=auth.user.id,
            action="restored",
            created_at=restored_at,
        )
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/work-overview", response_model=ProjectWorkOverviewRead)
def get_project_work_overview(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    require_workspace_project(db, workspace_id=workspace.id, project_id=project_id)
    return build_project_work_overview(project_id, db)


@router.get("/{project_id}/review-context", response_model=ProjectReviewSnapshotRead)
def get_project_review_context(
    project_id: int,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    return build_project_review_snapshot(
        project, workspace_id=workspace.id, user_id=auth.user.id, db=db
    )


@router.patch("/{project_id}/ai-context-policy", response_model=ProjectRead)
def update_project_ai_context_policy(
    project_id: int,
    policy: ProjectAIPolicyUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    require_active_project(project)
    if project.ai_context_enabled == policy.ai_context_enabled:
        return project
    db.add(
        ProjectAIPolicyEvent(
            workspace_id=workspace.id,
            project_id=project.id,
            actor_id=auth.user.id,
            previous_ai_context_enabled=project.ai_context_enabled,
            new_ai_context_enabled=policy.ai_context_enabled,
        )
    )
    project.ai_context_enabled = policy.ai_context_enabled
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_auth_context),
):
    workspace = request_workspace(db, auth)
    project = require_workspace_project(
        db, workspace_id=workspace.id, project_id=project_id
    )
    require_active_project(project)
    updates = project_data.model_dump(exclude_unset=True)
    previous_life_context = project.life_context
    for field, value in updates.items():
        setattr(project, field, value)
    if "life_context" in updates and project.life_context != previous_life_context:
        db.add(ProjectLifecycleEvent(
            workspace_id=workspace.id,
            project_id=project.id,
            actor_user_id=auth.user.id,
            action="life_context_changed",
            previous_life_context=previous_life_context,
            new_life_context=project.life_context,
        ))
    db.commit()
    db.refresh(project)
    return project
