"""Define provider-neutral AI contracts and safe provider failure types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.ai.context import WorkContext
from app.ai.provenance import SuggestionBasis
from app.ai.project_review import ProjectReviewResult
from app.ai.progress_review import ProgressReviewContext, ProgressReviewResult
from app.schemas.project_review import ProjectReviewSnapshotRead
from app.schemas.work_intake import WorkIntakeProposal, WorkIntakeSnapshot
from app.schemas.activity_report import ActivityReportResult, ActivityReportSnapshot


class AIProviderError(RuntimeError):
    """Safe boundary for provider failures that should not expose internals."""


class AIProviderTimeoutError(AIProviderError):
    """Raised when a provider does not finish inside Telaryn's review budget."""


class AIProviderInvalidResponseError(AIProviderError):
    """Raised when provider output fails Telaryn's structured response contract."""


@dataclass
class AIRecommendation:
    text: str
    rationale: str | None = None
    basis: SuggestionBasis = SuggestionBasis.RECOMMENDED


@dataclass
class AISuggestedAcceptanceCriterion:
    text: str
    basis: SuggestionBasis


@dataclass
class AISuggestedSubtask:
    title: str
    description: str | None
    basis: SuggestionBasis


@dataclass
class AISubtaskRevision:
    source_index: int
    suggested_title: str
    suggested_description: str | None = None
    rationale: str | None = None
    basis: SuggestionBasis = SuggestionBasis.INFERRED


@dataclass
class AIAcceptanceCriterionRevision:
    source_index: int
    suggested_text: str
    rationale: str | None = None
    basis: SuggestionBasis = SuggestionBasis.INFERRED


@dataclass
class AIReviewResult:
    suggested_title: str | None = None
    suggested_description: str | None = None
    suggested_priority: str | None = None
    suggested_ticket_type: str | None = None

    reasoning_summary: str | None = None

    missing_information: list[str] = field(default_factory=list)
    recommendations: list[AIRecommendation] = field(default_factory=list)
    acceptance_criteria: list[AISuggestedAcceptanceCriterion] = field(default_factory=list)
    suggested_subtasks: list[AISuggestedSubtask] = field(default_factory=list)
    subtask_revisions: list[AISubtaskRevision] = field(default_factory=list)
    acceptance_criteria_revisions: list[AIAcceptanceCriterionRevision] = field(
        default_factory=list
    )


class AIProvider(ABC):
    """Return structured, advisory proposals; persistence stays with Telaryn services."""
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    def propose_work_intake(
        self,
        snapshot: WorkIntakeSnapshot,
    ) -> WorkIntakeProposal:
        """Return a transient workspace-aware proposal without applying it."""
        raise AIProviderError("The configured provider does not support Work Intake.")

    def project_review_request_overhead(self) -> str:
        """Return stable non-snapshot text included with every Project Review call."""
        return ""

    def generate_activity_report(
        self, snapshot: ActivityReportSnapshot
    ) -> ActivityReportResult:
        """Synthesize an advisory report from Telaryn-selected evidence."""
        raise AIProviderError("The configured provider does not support Activity Reports.")

    def review_ticket_progress(
        self, context: ProgressReviewContext
    ) -> ProgressReviewResult:
        raise AIProviderError(
            "The configured provider does not support Ticket Progress Review."
        )

    def review_project(
        self,
        snapshot: ProjectReviewSnapshotRead,
    ) -> ProjectReviewResult:
        """Return a bounded project-level proposal without applying it."""
        raise AIProviderError("The configured provider does not support Project Review.")

    @abstractmethod
    def review_ticket(
        self,
        context: WorkContext,
    ) -> AIReviewResult:
        pass

