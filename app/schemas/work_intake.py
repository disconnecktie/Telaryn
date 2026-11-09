"""Define transient, non-authoritative Work Intake contracts."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.ai.provenance import SuggestionBasis


WorkIntakeAction = Literal[
    "create_project",
    "create_ticket",
    "create_tickets",
    "update_ticket",
    "use_existing",
    "needs_clarification",
]


class WorkIntakeRequest(BaseModel):
    source_text: str = Field(max_length=12000)

    @field_validator("source_text")
    @classmethod
    def require_source_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Describe the work Telaryn should help shape.")
        return value


class WorkIntakeClarificationRequest(BaseModel):
    answers: list[str] = Field(min_length=1, max_length=5)

    @field_validator("answers")
    @classmethod
    def normalize_answers(cls, values: list[str]) -> list[str]:
        answers = [value.strip()[:2000] for value in values]
        if not any(answers):
            raise ValueError("Answer at least one clarification question.")
        return answers


class WorkIntakeProjectCandidate(BaseModel):
    id: int
    reference: str
    name: str
    description: str | None = None
    purpose: str | None = None
    why_it_matters: str | None = None


class WorkIntakeTicketCandidate(BaseModel):
    id: int
    reference: str
    title: str
    description: str | None = None
    status: str
    priority: str
    ticket_type: str
    project_id: int | None = None
    project_name: str | None = None


class WorkIntakeSnapshot(BaseModel):
    source_text: str
    projects: list[WorkIntakeProjectCandidate]
    tickets: list[WorkIntakeTicketCandidate]
    clarification_questions: list[str] = Field(default_factory=list, max_length=5)
    clarification_answers: list[str] = Field(default_factory=list, max_length=5)
    refinement_count: int = Field(default=0, ge=0, le=1)


class ProposedProject(BaseModel):
    name: str
    description: str | None = None
    purpose: str | None = None
    why_it_matters: str | None = None


class ProposedStructureItem(BaseModel):
    text: str
    basis: SuggestionBasis | None = None

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_text(cls, value):
        """Read pre-provenance attempts without assigning unsupported meaning."""
        if isinstance(value, str):
            return {"text": value, "basis": None}
        return value


class ProposedTicket(BaseModel):
    title: str
    description: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    ticket_type: Literal[
        "task", "problem", "request", "research", "development"
    ] = "task"
    project_id: int | None = None
    acceptance_criteria: list[ProposedStructureItem] = Field(default_factory=list, max_length=7)
    subtasks: list[ProposedStructureItem] = Field(default_factory=list, max_length=7)


class ProposedTicketChanges(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    ticket_type: Literal[
        "task", "problem", "request", "research", "development"
    ] | None = None
    acceptance_criteria: list[ProposedStructureItem] = Field(default_factory=list, max_length=7)
    subtasks: list[ProposedStructureItem] = Field(default_factory=list, max_length=7)


class WorkIntakeProposal(BaseModel):
    action: WorkIntakeAction
    summary: str
    rationale: str
    confidence: Literal["low", "medium", "high"]
    target_project_id: int | None
    target_ticket_id: int | None
    proposed_project: ProposedProject | None
    proposed_tickets: list[ProposedTicket] = Field(max_length=8)
    proposed_ticket_changes: ProposedTicketChanges | None
    questions: list[str] = Field(max_length=5)
    is_provisional: bool = False
    clarification_prompt: str | None = None


class WorkIntakeRead(WorkIntakeProposal):
    provider: str
    model: str
    matched_projects: list[WorkIntakeProjectCandidate] = Field(default_factory=list)
    matched_tickets: list[WorkIntakeTicketCandidate] = Field(default_factory=list)
