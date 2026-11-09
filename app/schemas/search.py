"""Define bounded, contextual results for authorized Telaryn search."""

from enum import Enum

from pydantic import BaseModel, Field


class SearchResourceType(str, Enum):
    PROJECT = "project"
    TICKET = "ticket"
    ACCEPTANCE_CRITERION = "acceptance_criterion"
    SUBTASK = "subtask"


class SearchResult(BaseModel):
    resource_type: SearchResourceType
    id: int
    reference: str
    public_id: str | None = None
    title: str
    matched_field: str
    excerpt: str
    project_id: int | None = None
    project_reference: str | None = None
    project_name: str | None = None
    ticket_id: int | None = None
    ticket_reference: str | None = None
    ticket_title: str | None = None
    status: str | None = None
    archived: bool = False
    private: bool = False
    deferred: bool = False


class SearchRead(BaseModel):
    query: str
    projects: list[SearchResult] = Field(default_factory=list)
    tickets: list[SearchResult] = Field(default_factory=list)
    acceptance_criteria: list[SearchResult] = Field(default_factory=list)
    subtasks: list[SearchResult] = Field(default_factory=list)
    total: int = 0
    truncated: bool = False

