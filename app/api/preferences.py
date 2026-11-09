"""Read and save account/workspace defaults without modifying focus or tickets."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.workspace_membership import WorkspaceMembership
from app.services.auth import AuthContext, require_auth_context

router = APIRouter(prefix="/preferences", tags=["Preferences"])


class DefaultProject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_project_id: int | None = Field(..., strict=True, gt=0)


def member(db, auth):
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == auth.user.id,
        WorkspaceMembership.workspace_id == auth.workspace.id,
    ))
    if membership is None:
        raise HTTPException(status_code=403, detail="Workspace membership required.")
    return membership


def allowed_project(db, auth, project_id):
    return db.scalar(select(Project.id).where(
        Project.id == project_id,
        Project.workspace_id == auth.workspace.id,
        Project.archived_at.is_(None),
    )) if project_id is not None else None


@router.get("/", response_model=DefaultProject)
def read_preferences(db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context)):
    return DefaultProject(default_project_id=allowed_project(db, auth, member(db, auth).default_project_id))


@router.put("/", response_model=DefaultProject)
def save_preferences(payload: DefaultProject, db: Session = Depends(get_db), auth: AuthContext = Depends(require_auth_context)):
    project_id = payload.default_project_id
    if project_id is not None and allowed_project(db, auth, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    membership = member(db, auth)
    membership.default_project_id = project_id
    db.commit()
    return payload
