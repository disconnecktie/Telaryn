"""Provider-neutral contracts for bounded, human-governed Project Review."""

from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.provenance import SuggestionBasis


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectReviewOutcome(str, Enum):
    NO_MATERIAL_CONCERNS = "no_material_concerns"
    FINDINGS_ONLY = "findings_only"
    CHANGES_PROPOSED = "changes_proposed"


# Retain the Project Review name as a compatibility alias while all Telaryn AI
# surfaces share the same provider-neutral vocabulary.
ProjectReviewBasis = SuggestionBasis


class ProjectReviewSignificance(str, Enum):
    NECESSARY = "necessary"
    IMPORTANT = "important"


class ProjectReviewProposalType(str, Enum):
    CREATE_TICKET = "create_ticket"
    EDIT_TICKET = "edit_ticket"
    CHANGE_TICKET_PRIORITY = "change_ticket_priority"
    ADD_ACCEPTANCE_CRITERIA = "add_acceptance_criteria"
    ADD_SUBTASKS = "add_subtasks"
    UPDATE_PROJECT_CONTEXT = "update_project_context"
    RECOMMEND_CURRENT_FOCUS = "recommend_current_focus"


class ProjectReviewEvidenceSource(str, Enum):
    PROJECT_FIELD = "project_field"
    TICKET = "ticket"
    ACCEPTANCE_CRITERION = "acceptance_criterion"
    SUBTASK = "subtask"
    TICKET_UPDATE = "ticket_update"
    WORK_OVERVIEW_SIGNAL = "work_overview_signal"
    ACTIVITY_EVENT = "activity_event"
    STATUS_EVENT = "status_event"


ShortText = Annotated[str, Field(min_length=1, max_length=500)]
LongText = Annotated[str, Field(min_length=1, max_length=5000)]
TitleText = Annotated[str, Field(min_length=1, max_length=200)]


class ProjectReviewEvidence(_StrictModel):
    source_type: ProjectReviewEvidenceSource
    source_id: int
    field_name: str | None = Field(max_length=80)
    summary: str = Field(min_length=1, max_length=500)


class ProjectReviewFinding(_StrictModel):
    summary: str = Field(min_length=1, max_length=500)
    basis: ProjectReviewBasis
    significance: ProjectReviewSignificance
    evidence: list[ProjectReviewEvidence] = Field(min_length=1, max_length=5)


class ProjectReviewRisk(_StrictModel):
    summary: str = Field(min_length=1, max_length=500)
    basis: ProjectReviewBasis
    significance: ProjectReviewSignificance
    evidence: list[ProjectReviewEvidence] = Field(min_length=1, max_length=5)


class ProjectReviewGuidance(_StrictModel):
    summary: str = Field(min_length=1, max_length=500)
    basis: ProjectReviewBasis
    evidence: list[ProjectReviewEvidence] = Field(max_length=5)


class ProjectReviewProposedChanges(_StrictModel):
    title: TitleText | None
    description: LongText | None
    priority: Literal["low", "medium", "high", "critical"] | None
    ticket_type: Literal["task", "problem", "request", "research", "development"] | None
    acceptance_criteria: list[ShortText] = Field(max_length=20)
    subtasks: list[ShortText] = Field(max_length=20)
    project_description: LongText | None
    project_purpose: LongText | None
    project_why_it_matters: LongText | None
    project_target_date: date | None


class ProjectReviewProposal(_StrictModel):
    proposal_type: ProjectReviewProposalType
    summary: str = Field(min_length=1, max_length=500)
    basis: ProjectReviewBasis
    significance: ProjectReviewSignificance
    evidence: list[ProjectReviewEvidence] = Field(min_length=1, max_length=5)
    target_project_id: int | None
    target_ticket_id: int | None
    proposed_changes: ProjectReviewProposedChanges


class ProjectReviewFocusRecommendation(_StrictModel):
    ticket_id: int
    rationale: str = Field(min_length=1, max_length=500)
    basis: ProjectReviewBasis
    evidence: list[ProjectReviewEvidence] = Field(min_length=1, max_length=5)


class ProjectReviewResult(_StrictModel):
    outcome: ProjectReviewOutcome
    summary: str = Field(min_length=1, max_length=1000)
    findings: list[ProjectReviewFinding] = Field(max_length=3)
    risks: list[ProjectReviewRisk] = Field(max_length=3)
    planning_guidance: list[ProjectReviewGuidance] = Field(max_length=5)
    proposals: list[ProjectReviewProposal] = Field(max_length=5)
    recommended_focus: ProjectReviewFocusRecommendation | None

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.outcome == ProjectReviewOutcome.CHANGES_PROPOSED and not self.proposals:
            raise ValueError("changes_proposed requires at least one proposal")
        if self.outcome != ProjectReviewOutcome.CHANGES_PROPOSED and self.proposals:
            raise ValueError("proposals require the changes_proposed outcome")
        return self

