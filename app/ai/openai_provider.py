"""Translate Telaryn work context into bounded, schema-constrained OpenAI reviews."""

from typing import Literal

from openai import APIError, APITimeoutError, OpenAI
from pydantic import BaseModel, ConfigDict, ValidationError

from app.ai.base import (
    AIAcceptanceCriterionRevision,
    AIProvider,
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderTimeoutError,
    AIRecommendation,
    AIReviewResult,
    AISuggestedAcceptanceCriterion,
    AISuggestedSubtask,
    AISubtaskRevision,
)
from app.ai.context import WorkContext
from app.ai.provenance import SuggestionBasis
from app.ai.project_review import ProjectReviewResult
from app.ai.progress_review import (
    ProgressReviewContext,
    ProgressReviewResult,
    ProgressSuggestion,
)
from app.schemas.project_review import ProjectReviewSnapshotRead
from app.schemas.work_intake import WorkIntakeProposal, WorkIntakeSnapshot
from app.schemas.activity_report import ActivityReportResult, ActivityReportSnapshot


class _StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _RecommendationOutput(_StrictOutput):
    text: str
    rationale: str | None
    basis: SuggestionBasis


class _ProposedTextOutput(_StrictOutput):
    text: str
    basis: SuggestionBasis


class _SubtaskOutput(_StrictOutput):
    title: str
    description: str | None
    basis: SuggestionBasis


class _SubtaskRevisionOutput(_StrictOutput):
    source_index: int
    suggested_title: str
    suggested_description: str | None
    rationale: str | None
    basis: SuggestionBasis


class _CriterionRevisionOutput(_StrictOutput):
    source_index: int
    suggested_text: str
    rationale: str | None
    basis: SuggestionBasis


class _WorkIntakeProjectOutput(_StrictOutput):
    name: str
    description: str | None
    purpose: str | None
    why_it_matters: str | None


class _WorkIntakeTicketOutput(_StrictOutput):
    title: str
    description: str | None
    priority: Literal["low", "medium", "high", "critical"]
    ticket_type: Literal["task", "problem", "request", "research", "development"]
    project_id: int | None
    acceptance_criteria: list[_ProposedTextOutput]
    subtasks: list[_ProposedTextOutput]


class _WorkIntakeTicketChangesOutput(_StrictOutput):
    title: str | None
    description: str | None
    priority: Literal["low", "medium", "high", "critical"] | None
    ticket_type: Literal[
        "task", "problem", "request", "research", "development"
    ] | None
    acceptance_criteria: list[_ProposedTextOutput]
    subtasks: list[_ProposedTextOutput]


class _WorkIntakeOutput(_StrictOutput):
    action: Literal[
        "create_project",
        "create_ticket",
        "create_tickets",
        "update_ticket",
        "use_existing",
        "needs_clarification",
    ]
    summary: str
    rationale: str
    confidence: Literal["low", "medium", "high"]
    target_project_id: int | None
    target_ticket_id: int | None
    proposed_project: _WorkIntakeProjectOutput | None
    proposed_tickets: list[_WorkIntakeTicketOutput]
    proposed_ticket_changes: _WorkIntakeTicketChangesOutput | None
    questions: list[str]
    is_provisional: bool
    clarification_prompt: str | None


class _TicketReviewOutput(_StrictOutput):
    """Single source for provider validation and the Responses JSON schema."""

    suggested_title: str | None
    suggested_description: str | None
    suggested_priority: Literal["low", "medium", "high", "critical"] | None
    suggested_ticket_type: Literal[
        "task", "problem", "request", "research", "development"
    ] | None
    reasoning_summary: str | None
    missing_information: list[str]
    recommendations: list[_RecommendationOutput]
    acceptance_criteria: list[_ProposedTextOutput]
    suggested_subtasks: list[_SubtaskOutput]
    subtask_revisions: list[_SubtaskRevisionOutput]
    acceptance_criteria_revisions: list[_CriterionRevisionOutput]


class _ProgressSuggestionOutput(_StrictOutput):
    kind: Literal["acceptance_criterion", "subtask"]
    item_id: int
    rationale: str


class _ProgressReviewOutput(_StrictOutput):
    summary: str
    suggestions: list[_ProgressSuggestionOutput]


PROJECT_REVIEW_INSTRUCTIONS = (
    "You are Telaryn conducting an explicitly requested project health and planning review. "
    "Use only the supplied bounded snapshot. Do not invent facts or propose status changes, "
    "completion, cancellation, archival, deletion, project moves, or automatic merging. "
    "Allowed proposal types are create_ticket, edit_ticket, change_ticket_priority, "
    "add_acceptance_criteria, add_subtasks, update_project_context, and recommend_current_focus. "
    "Project context changes require clear material evidence. Return at most three findings, "
    "three risks, five guidance items, five proposals, and one focus recommendation. "
    "Classify claims as supported, inferred, or recommended and significance as necessary or important. "
    "Every supported or inferred item must cite evidence that exists in the supplied snapshot. Use only exact "
    "snapshot IDs: project_field uses the Project ID and one of name, description, purpose, why_it_matters, "
    "or target_date; ticket, acceptance_criterion, subtask, and ticket_update use their matching IDs; "
    "activity_event and status_event use exact recent_activity source IDs; work_overview_signal uses the "
    "Project ID or an attention Ticket ID and one of attention, tickets, acceptance_criteria, subtasks, or "
    "current_focus. Recommend Current Focus only for a Ticket whose detail_included value is true. "
    "Proposal payload rules are exact: create_ticket targets this Project, has no target Ticket, and includes "
    "a title; edit_ticket targets an active Ticket and changes only title or description; "
    "change_ticket_priority includes only priority; add_acceptance_criteria includes only acceptance_criteria; "
    "add_subtasks includes only subtasks; update_project_context targets this Project, has no target Ticket, "
    "and uses only project_description, project_purpose, project_why_it_matters, or project_target_date; "
    "recommend_current_focus targets an active Ticket and contains no proposed changes. Leave every unrelated "
    "proposed_changes field null or empty. Use changes_proposed only when proposals is non-empty, and use another "
    "outcome when proposals is empty. Omit any item you cannot ground within these rules. "
    "It is valid—and preferred when appropriate—to report no material concerns or findings without changes."
)


WORK_INTAKE_INSTRUCTIONS = (
    "You are Telaryn shaping rough work before anything becomes authoritative. "
    "Use only the supplied authorized snapshot. Decide whether the best outcome is "
    "create_project, create_ticket, create_tickets, update_ticket, use_existing, "
    "or needs_clarification. Existing-work matches must use exact supplied numeric IDs. "
    "Never invent an existing Project or Ticket. Prefer existing work when it materially "
    "covers the request, but do not force unrelated work together. A Project represents "
    "a larger outcome with multiple deliverables; a Ticket represents one bounded "
    "deliverable. A new Project may include between one and eight starter Tickets; "
    "prefer three to five distinct deliverables when the scope warrants it. Return "
    "exactly one Ticket for create_ticket and between two and eight Tickets for "
    "create_tickets. Never split simple steps into unnecessary micro-Tickets. If more "
    "than eight Tickets appear necessary, propose the first coherent phase and explain "
    "that additional planning should follow. Every proposed Ticket must include between one and "
    "seven measurable acceptance criteria and between one and seven concrete subtasks. Choose "
    "each count from the actual scope, not from the provenance categories; one item may be enough, "
    "two to five is typical for substantive work, and six or seven should appear only when the "
    "deliverable genuinely needs them. Acceptance criteria describe independently verifiable "
    "completion outcomes. Subtasks describe concrete actions needed to produce those outcomes. "
    "Do not duplicate the same statement as both a criterion and a subtask. "
    "Classify every proposed acceptance criterion and subtask as supported, inferred, "
    "or recommended. Supported means directly stated by the supplied source; inferred "
    "means a reasonable implication; recommended means optional guidance or best practice. "
    "Do not present recommended items as requirements. Provenance labels explain why an item "
    "was proposed; they are not slots to fill. Do not add an item merely to represent a label, "
    "and allow zero, one, or several items with any label when the evidence warrants it. "
    "Assess whether the supplied context is sufficient for an actionable proposal. "
    "When a useful provisional Project or Ticket can be constructed but material details "
    "are missing, return that actionable proposal, set is_provisional true, provide a plain "
    "clarification_prompt, and ask only the concise questions whose answers could "
    "materially change scope, placement, outcomes, steps, priority, or next action. Do not ask "
    "more than five questions, but do not fill that allowance when fewer questions are useful. "
    "for facts already present in the source, candidates, or clarification answers. Use "
    "needs_clarification only when no safe actionable proposal can be constructed. When the "
    "snapshot refinement_count is one, incorporate clarification_answers, set is_provisional "
    "false, return no questions, and produce the best bounded result without requesting another "
    "round. For update_ticket, include only "
    "changes supported by the source text. "
    "For use_existing, propose no changes. Explain the recommendation plainly. "
    "This is advisory: do not claim anything was created, changed, approved, or saved."
)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        reasoning_effort: str,
    ):
        # Disable SDK retries so Telaryn's configured deadline remains meaningful.
        self.client = OpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_activity_report(
        self, snapshot: ActivityReportSnapshot
    ) -> ActivityReportResult:
        """Synthesize outcomes from bounded evidence without inventing impact."""
        try:
            response = self.client.responses.create(
                model=self._model,
                store=False,
                instructions=(
                    "You are Telaryn, producing an activity report from authorized evidence. "
                    "Use the supplied subject_first_name exactly when naming the person whose "
                    "accomplishments are being reported; never refer to them as 'the user'. "
                    "Describe what that person accomplished and why it mattered. Treat Telaryn as the "
                    "organizer of evidence, never as the actor receiving credit. When the work is "
                    "development of Telaryn itself, credit the user with building or improving the "
                    "product rather than saying Telaryn performed the work. Synthesize meaningful "
                    "outcomes, progress, results, and supported impact; do not merely list every "
                    "Ticket. Never invent facts, metrics, ownership, or impact. Omit unsupported "
                    "claims. Preserve the requested output format. "
                    "For narrative output, return concise professional paragraphs. For "
                    "action_result_impact output, every item must explicitly state Action, "
                    "Result, and Impact; state that impact is not yet documented when evidence "
                    "does not support one. The optional style example controls tone only and is "
                    "not factual evidence. Return structured JSON only."
                ),
                input=snapshot.model_dump_json(),
                reasoning={"effort": self._reasoning_effort},
                max_output_tokens=self._max_output_tokens,
                text={
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "atlas_activity_report",
                        "strict": True,
                        "schema": ActivityReportResult.model_json_schema(),
                    },
                },
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError(
                "The AI provider did not respond before Telaryn's timeout."
            ) from error
        except APIError as error:
            raise AIProviderError("The AI provider request failed.") from error
        try:
            return ActivityReportResult.model_validate_json(response.output_text)
        except ValidationError as error:
            raise AIProviderInvalidResponseError(
                "The AI provider returned an invalid Activity Report."
            ) from error

    def propose_work_intake(
        self, snapshot: WorkIntakeSnapshot
    ) -> WorkIntakeProposal:
        """Classify rough work against a bounded authorized workspace snapshot."""
        try:
            response = self.client.responses.create(
                model=self._model,
                store=False,
                instructions=WORK_INTAKE_INSTRUCTIONS,
                input=snapshot.model_dump_json(),
                reasoning={"effort": self._reasoning_effort},
                max_output_tokens=self._max_output_tokens,
                text={
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "atlas_work_intake",
                        "strict": True,
                        "schema": _WorkIntakeOutput.model_json_schema(),
                    },
                },
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError(
                "The AI provider did not respond before Telaryn's timeout."
            ) from error
        except APIError as error:
            raise AIProviderError("The AI provider request failed.") from error

        try:
            output = _WorkIntakeOutput.model_validate_json(response.output_text)
            proposal = output.model_dump()
            proposal["questions"] = proposal["questions"][:5]
            proposal["proposed_tickets"] = proposal["proposed_tickets"][:8]
            for ticket in proposal["proposed_tickets"]:
                ticket["acceptance_criteria"] = ticket["acceptance_criteria"][:7]
                ticket["subtasks"] = ticket["subtasks"][:7]
            if proposal["proposed_ticket_changes"] is not None:
                changes = proposal["proposed_ticket_changes"]
                changes["acceptance_criteria"] = changes["acceptance_criteria"][:7]
                changes["subtasks"] = changes["subtasks"][:7]
            return WorkIntakeProposal.model_validate(proposal)
        except ValidationError as error:
            raise AIProviderInvalidResponseError(
                "The AI provider returned an invalid Work Intake proposal."
            ) from error

    def review_project(self, snapshot: ProjectReviewSnapshotRead) -> ProjectReviewResult:
        """Generate a strict, bounded project review from Telaryn-selected context."""
        try:
            response = self.client.responses.create(
                model=self._model,
                store=False,
                instructions=PROJECT_REVIEW_INSTRUCTIONS,
                input=snapshot.model_dump_json(),
                reasoning={"effort": self._reasoning_effort},
                max_output_tokens=self._max_output_tokens,
                text={
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "atlas_project_review",
                        "strict": True,
                        "schema": ProjectReviewResult.model_json_schema(),
                    },
                },
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError(
                "The AI provider did not respond before Telaryn's timeout."
            ) from error
        except APIError as error:
            raise AIProviderError("The AI provider request failed.") from error

        try:
            return ProjectReviewResult.model_validate_json(response.output_text)
        except ValidationError as error:
            raise AIProviderInvalidResponseError(
                "The AI provider returned an invalid structured Project Review."
            ) from error

    def review_ticket_progress(self, context: ProgressReviewContext) -> ProgressReviewResult:
        payload = {
            "newly_recorded_evidence": context.evidence,
            "evidence_type": context.evidence_type,
            "candidates": [candidate.__dict__ for candidate in context.candidates],
        }
        try:
            response = self.client.responses.create(
                model=self._model, store=False,
                instructions=(
                    "Review only the supplied newly recorded evidence against the supplied unfinished "
                    "ticket items. Suggest completion only when the evidence directly supports it. "
                    "Never infer unrelated work. Return at most five suggestions and preserve the exact "
                    "kind and item_id values supplied by Telaryn. Suggestions are advisory."
                ),
                input=str(payload), reasoning={"effort": self._reasoning_effort},
                max_output_tokens=self._max_output_tokens,
                text={"verbosity": "low", "format": {"type": "json_schema",
                    "name": "atlas_ticket_progress_review", "strict": True,
                    "schema": _ProgressReviewOutput.model_json_schema()}},
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError("The AI provider did not respond before Telaryn's timeout.") from error
        except APIError as error:
            raise AIProviderError("The AI provider request failed.") from error
        try:
            data = _ProgressReviewOutput.model_validate_json(response.output_text)
        except ValidationError as error:
            raise AIProviderInvalidResponseError("The AI provider returned an invalid progress review.") from error
        allowed = {(item.kind, item.item_id) for item in context.candidates}
        return ProgressReviewResult(summary=data.summary, suggestions=[
            ProgressSuggestion(kind=item.kind, item_id=item.item_id, rationale=item.rationale)
            for item in data.suggestions[:5] if (item.kind, item.item_id) in allowed
        ])

    def review_ticket(
        self,
        context: WorkContext,
    ) -> AIReviewResult:
        subtasks_text = "\n".join(
            (
                f"- [{index}] [{subtask.status}] {subtask.title}"
                + (
                    f": {subtask.description}"
                    if subtask.description
                    else ""
                )
            )
            for index, subtask in enumerate(context.subtasks)
        )

        if not subtasks_text:
            subtasks_text = "None"

        criteria_text = "\n".join(
            f"- [{index}] [{'done' if criterion.completed else 'open'}] {criterion.text}"
            for index, criterion in enumerate(context.acceptance_criteria)
        )

        if not criteria_text:
            criteria_text = "None"

        try:
            response = self.client.responses.create(
                model=self._model,
                store=False,
                instructions=(
                    "You are Telaryn, an AI assistant for structured work management. "
                    "Review the full work context and improve the ticket without inventing facts. "
                    "Treat existing subtasks as evidence of intent and progress. "
                    "Do not suggest work that is already represented by an existing subtask. "
                    "Return ONLY valid JSON. "
                    "Use concise standalone titles. "
                    "Identify missing information explicitly. "
                    "Suggest measurable acceptance criteria. "
                    "Break work into meaningful, non-redundant subtasks. "
                    "Review each existing subtask and acceptance criterion. When a clearer, "
                    "more testable version is materially needed, propose a revision keyed to "
                    "its numeric source index. Do not rewrite items that are already clear. "
                    "Return no more than five additions and five revisions for each structure "
                    "type. Keep rationales and summaries concise. Never invent new facts. "
                    "Priority must be one of: low, medium, high, critical. "
                    "Ticket type must be one of: task, problem, request, research, development. "
                    "Separate missing requirements from optional recommendations. "
                    "Do not present best practices as established requirements unless the context supports them. "
                    "Recommendations should be clearly advisory and include a concise rationale. "
                    "Classify every recommendation, suggested acceptance criterion, suggested subtask, and revision "
                    "with basis supported, inferred, or recommended. Supported means directly stated by supplied "
                    "context; inferred means a reasonable implication that is not explicit; recommended means an "
                    "optional improvement or best practice. "
                ),
                input=(
                    f"PROJECT:\n{context.project_name or 'None'}\n\n"
                    f"TITLE:\n{context.title}\n\n"
                    f"DESCRIPTION:\n{context.description or ''}\n\n"
                    f"STATUS:\n{context.status}\n\n"
                    f"PRIORITY:\n{context.priority}\n\n"
                    f"TICKET TYPE:\n{context.ticket_type}\n\n"
                    f"EXISTING SUBTASKS:\n{subtasks_text}\n\n"
                    f"EXISTING ACCEPTANCE CRITERIA:\n{criteria_text}\n\n"
                    "Review the ticket as a whole. "
                    "Existing subtasks are evidence of the ticket's intent and current work. "
                    "Do not duplicate existing acceptance criteria. "
                    "Do not duplicate existing work. "
                    "Do not invent facts that are not supported by the provided context.\n\n"
                    "Return the requested structured review. Use empty arrays when no "
                    "changes are warranted and null for unchanged ticket fields."
                ),
                reasoning={"effort": self._reasoning_effort},
                max_output_tokens=self._max_output_tokens,
                text={
                    "verbosity": "low",
                    "format": {
                        "type": "json_schema",
                        "name": "atlas_ticket_review",
                        "strict": True,
                        "schema": _TicketReviewOutput.model_json_schema(),
                    },
                },
            )
        except APITimeoutError as error:
            raise AIProviderTimeoutError(
                "The AI provider did not respond before Telaryn's timeout."
            ) from error
        except APIError as error:
            raise AIProviderError("The AI provider request failed.") from error

        try:
            data = _TicketReviewOutput.model_validate_json(response.output_text)
        except ValidationError as error:
            raise AIProviderError(
                "The AI provider returned an invalid structured review."
            ) from error

        return AIReviewResult(
            suggested_title=data.suggested_title,
            suggested_description=data.suggested_description,
            suggested_priority=data.suggested_priority,
            suggested_ticket_type=data.suggested_ticket_type,
            reasoning_summary=data.reasoning_summary,
            missing_information=data.missing_information[:5],
            recommendations=[
                AIRecommendation(
                    text=item.text,
                    rationale=item.rationale,
                    basis=item.basis,
                )
                for item in data.recommendations[:5]
            ],
            acceptance_criteria=[
                AISuggestedAcceptanceCriterion(text=item.text, basis=item.basis)
                for item in data.acceptance_criteria[:5]
            ],
            suggested_subtasks=[
                AISuggestedSubtask(
                    title=item.title,
                    description=item.description,
                    basis=item.basis,
                )
                for item in data.suggested_subtasks[:5]
            ],
            subtask_revisions=[
                AISubtaskRevision(
                    source_index=item.source_index,
                    suggested_title=item.suggested_title,
                    suggested_description=item.suggested_description,
                    rationale=item.rationale,
                    basis=item.basis,
                )
                for item in data.subtask_revisions[:5]
            ],
            acceptance_criteria_revisions=[
                AIAcceptanceCriterionRevision(
                    source_index=item.source_index,
                    suggested_text=item.suggested_text,
                    rationale=item.rationale,
                    basis=item.basis,
                )
                for item in data.acceptance_criteria_revisions[:5]
            ],
        )
