"""Safe identity-lifecycle contracts; intentionally exclude workspace content."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserLifecycleAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: Literal[True]


class WorkspaceMembershipRoleAction(UserLifecycleAction):
    role: Literal["owner", "member"]


class ManagedWorkspaceRead(BaseModel):
    id: int
    name: str
    role: str


class ManagedUserRead(BaseModel):
    id: int
    email: str
    display_name: str
    account_status: Literal["active", "disabled"]
    created_at: datetime
    disabled_at: datetime | None
    workspace_count: int


class ManagedUserDetailRead(ManagedUserRead):
    workspaces: list[ManagedWorkspaceRead]
    session_count: int
    active_session_count: int


class ManagedUserPage(BaseModel):
    items: list[ManagedUserRead]
    total: int
    page: int
    pages: int


class DeploymentAdminAccess(BaseModel):
    allowed: bool
