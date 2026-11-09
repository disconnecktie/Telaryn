"""Deterministic AI provider used for local development and behavioral tests."""

from app.ai.base import (
    AIAcceptanceCriterionRevision,
    AIProvider,
    AIRecommendation,
    AIReviewResult,
    AISuggestedAcceptanceCriterion,
    AISuggestedSubtask,
    AISubtaskRevision,
)
from app.ai.provenance import SuggestionBasis
from app.ai.progress_review import (
    ProgressReviewContext,
    ProgressReviewResult,
    ProgressSuggestion,
)
from app.ai.context import WorkContext
from app.ai.project_review import (
    ProjectReviewBasis,
    ProjectReviewEvidence,
    ProjectReviewFinding,
    ProjectReviewOutcome,
    ProjectReviewResult,
    ProjectReviewSignificance,
)
from app.schemas.project_review import ProjectReviewSnapshotRead
from app.schemas.work_intake import (
    ProposedProject,
    ProposedStructureItem,
    ProposedTicket,
    WorkIntakeProposal,
    WorkIntakeSnapshot,
)
from app.schemas.activity_report import ActivityReportResult, ActivityReportSnapshot


class MockAIProvider(AIProvider):
    def review_ticket_progress(self, context: ProgressReviewContext) -> ProgressReviewResult:
        evidence = context.evidence.casefold()
        suggestions = []
        for candidate in context.candidates:
            meaningful = [word for word in candidate.text.casefold().split() if len(word) > 4]
            if any(word.strip(".,:;()") in evidence for word in meaningful):
                suggestions.append(ProgressSuggestion(
                    kind=candidate.kind,
                    item_id=candidate.item_id,
                    rationale="The newly recorded update directly describes work represented by this item.",
                ))
        return ProgressReviewResult(
            summary="Telaryn compared the newly recorded evidence with unfinished ticket scope.",
            suggestions=suggestions[:5],
        )

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-v2"

    def generate_activity_report(
        self, snapshot: ActivityReportSnapshot
    ) -> ActivityReportResult:
        items = []
        for project in snapshot.projects:
            ticket_titles = ", ".join(ticket.title for ticket in project.tickets[:4])
            if snapshot.output_format == "action_result_impact":
                items.append(
                    f"Action: {snapshot.subject_first_name} advanced {project.name} through {ticket_titles}. "
                    "Result: Recorded measurable progress in Telaryn. "
                    f"Impact: Moved {project.purpose or 'the project outcome'} forward."
                )
            else:
                items.append(
                    f"{snapshot.subject_first_name} advanced {project.name} through {ticket_titles}, creating documented "
                    f"progress toward {project.purpose or 'the intended project outcome'}."
                )
        return ActivityReportResult(
            title=f"{snapshot.period.title()} Activity Report",
            items=items,
        )

    def propose_work_intake(
        self, snapshot: WorkIntakeSnapshot
    ) -> WorkIntakeProposal:
        """Return deterministic advisory intake behavior for local development."""
        source = snapshot.source_text.strip()
        normalized = source.lower()
        if "already exists" in normalized and snapshot.tickets:
            ticket = snapshot.tickets[0]
            return WorkIntakeProposal(
                action="use_existing",
                summary=f"{ticket.reference} may already represent this work.",
                rationale="The request explicitly asks Telaryn to check existing work.",
                confidence="medium",
                target_project_id=ticket.project_id,
                target_ticket_id=ticket.id,
                proposed_project=None,
                proposed_tickets=[],
                proposed_ticket_changes=None,
                questions=[],
            )
        if "project" in normalized or "multiple" in normalized:
            title = source.splitlines()[0][:80].rstrip(" .")
            return WorkIntakeProposal(
                action="create_project",
                summary="This appears larger than one bounded Ticket.",
                rationale="The request describes a broader outcome with multiple pieces of work.",
                confidence="medium",
                target_project_id=None,
                target_ticket_id=None,
                proposed_project=ProposedProject(
                    name=title or "New work",
                    description=source,
                    purpose="Organize the requested outcome into reviewable work.",
                ),
                proposed_tickets=[
                    ProposedTicket(
                        title="Define the first project milestone",
                        description="Confirm the first bounded outcome and its delivery boundary.",
                        acceptance_criteria=[
                            ProposedStructureItem(text="The first milestone has a documented, reviewable outcome.", basis=SuggestionBasis.INFERRED),
                            ProposedStructureItem(text="The milestone boundary is approved before execution begins.", basis=SuggestionBasis.RECOMMENDED),
                        ],
                        subtasks=[
                            ProposedStructureItem(text="Confirm the intended first outcome.", basis=SuggestionBasis.INFERRED),
                            ProposedStructureItem(text="Document the milestone scope and completion evidence.", basis=SuggestionBasis.RECOMMENDED),
                        ],
                    ),
                    ProposedTicket(
                        title="Plan the remaining project deliverables",
                        description="Turn the broader outcome into a sequenced delivery plan.",
                        acceptance_criteria=[
                            ProposedStructureItem(text="The remaining deliverables are identified and ordered.", basis=SuggestionBasis.INFERRED),
                            ProposedStructureItem(text="Each deliverable has an owner-ready next action.", basis=SuggestionBasis.RECOMMENDED),
                        ],
                        subtasks=[
                            ProposedStructureItem(text="List the remaining deliverables.", basis=SuggestionBasis.INFERRED),
                            ProposedStructureItem(text="Sequence the work and record the next action for each item.", basis=SuggestionBasis.RECOMMENDED),
                        ],
                    ),
                ],
                proposed_ticket_changes=None,
                questions=[],
            )
        project_id = snapshot.projects[0].id if snapshot.projects else None
        return WorkIntakeProposal(
            action="create_ticket",
            summary="This looks like one bounded deliverable.",
            rationale="The request can be represented and reviewed as a single Ticket.",
            confidence="medium",
            target_project_id=project_id,
            target_ticket_id=None,
            proposed_project=None,
            proposed_tickets=[
                ProposedTicket(
                    title=source.splitlines()[0][:80].rstrip(" ."),
                    description=source,
                    project_id=project_id,
                    acceptance_criteria=[ProposedStructureItem(text="The requested outcome is complete and reviewed.", basis=SuggestionBasis.INFERRED)],
                    subtasks=[
                        ProposedStructureItem(text="Confirm the expected outcome.", basis=SuggestionBasis.INFERRED),
                        ProposedStructureItem(text="Complete the work.", basis=SuggestionBasis.SUPPORTED),
                    ],
                )
            ],
            proposed_ticket_changes=None,
            questions=[],
        )

    def review_project(self, snapshot: ProjectReviewSnapshotRead) -> ProjectReviewResult:
        """Return useful deterministic findings without manufacturing changes."""
        attention = snapshot.work_overview.attention
        if not attention:
            return ProjectReviewResult(
                outcome=ProjectReviewOutcome.NO_MATERIAL_CONCERNS,
                summary="No material health or planning concerns were found in the bounded project context.",
                findings=[],
                risks=[],
                planning_guidance=[],
                proposals=[],
                recommended_focus=None,
            )

        findings = []
        for item in attention[:3]:
            findings.append(
                ProjectReviewFinding(
                    summary=f"{item.title}: {', '.join(item.reasons)}",
                    basis=ProjectReviewBasis.SUPPORTED,
                    significance=ProjectReviewSignificance.IMPORTANT,
                    evidence=[
                        ProjectReviewEvidence(
                            source_type="work_overview_signal",
                            source_id=item.id,
                            field_name="attention",
                            summary=", ".join(item.reasons) or "Ticket requires attention",
                        )
                    ],
                )
            )
        return ProjectReviewResult(
            outcome=ProjectReviewOutcome.FINDINGS_ONLY,
            summary="Telaryn found project signals worth reviewing, but no structural change is necessary yet.",
            findings=findings,
            risks=[],
            planning_guidance=[],
            proposals=[],
            recommended_focus=None,
        )

    def review_ticket(
        self,
        context: WorkContext,
    ) -> AIReviewResult:
        normalized_title = context.title.strip()
        description = context.description
        subtask_revisions = [
            AISubtaskRevision(
                source_index=index,
                suggested_title=subtask.title.strip(),
                suggested_description=(
                    subtask.description
                    or f'Complete "{subtask.title.strip()}" and verify the expected result.'
                ),
                rationale=(
                    "Adds a clear completion check to the manually entered subtask."
                ),
            )
            for index, subtask in enumerate(context.subtasks)
        ]
        acceptance_criteria_revisions = [
            AIAcceptanceCriterionRevision(
                source_index=index,
                suggested_text=(
                    criterion.text.strip()
                    if criterion.text.strip().lower().startswith("verify")
                    else f"Verify that {criterion.text.strip().rstrip('.').lower()}."
                ),
                rationale=(
                    "Reframes the criterion as a directly verifiable completion condition."
                ),
            )
            for index, criterion in enumerate(context.acceptance_criteria)
        ]

        if not normalized_title:
            normalized_title = (
                (description or "Untitled work").splitlines()[0].strip()[:80]
            )

        if "high side" in normalized_title.lower():
            return AIReviewResult(
                suggested_title="Plan Telaryn deployment to high-side environment",
                suggested_description=(
                    "Determine the technical, dependency, authentication, "
                    "database, AI integration, and deployment requirements "
                    "needed to reconstruct and operate Telaryn within the "
                    "high-side environment."
                ),
                suggested_priority="high",
                suggested_ticket_type="development",
                reasoning_summary=(
                    "This is a constrained-environment deployment effort rather "
                    "than a simple installation task. Several infrastructure "
                    "dependencies must be validated before implementation."
                ),
                missing_information=[
                    "Which Python version is available in the target environment?",
                    "Which Node.js version is available?",
                    "Which Python and npm packages are available through the internal repositories?",
                    "What database service or database engine is approved?",
                    "How will PKI-authenticated identity be exposed to Telaryn?",
                    "What interface is available for the approved AI service?",
                    "What source-code transfer and deployment process is permitted?",
                ],
                acceptance_criteria=[
                    AISuggestedAcceptanceCriterion(text=text, basis=SuggestionBasis.INFERRED)
                    for text in [
                        "Required runtime dependencies are identified and available.",
                        "Telaryn can be reconstructed from approved source artifacts.",
                        "Database connectivity is validated.",
                        "PKI authentication approach is defined.",
                        "Approved AI provider integration is defined.",
                        "Frontend can be built and served in the target environment.",
                        "Telaryn successfully runs without public internet access.",
                    ]
                ],
                suggested_subtasks=[
                    AISuggestedSubtask(
                        title="Inventory target environment",
                        description=(
                            "Document available Python, Node.js, database, "
                            "web-hosting, and development tooling."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Validate internal package availability",
                        description=(
                            "Confirm required Python and npm dependencies exist "
                            "in approved internal repositories."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Define PKI integration approach",
                        description=(
                            "Determine how authenticated certificate identity "
                            "will map to Telaryn users."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Define high-side AI provider",
                        description=(
                            "Document the approved AI endpoint and implement "
                            "the Telaryn provider adapter."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Validate database deployment",
                        description=(
                            "Determine the approved database backend and confirm "
                            "Telaryn migrations operate correctly."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Validate frontend build process",
                        description=(
                            "Confirm React/Vite can be rebuilt using approved "
                            "Node.js and internal npm packages."
                        ),
                        basis=SuggestionBasis.INFERRED,
                    ),
                    AISuggestedSubtask(
                        title="Document deployment procedure",
                        description=(
                            "Create a reproducible procedure for reconstructing "
                            "and running Telaryn in the target environment."
                        ),
                        basis=SuggestionBasis.RECOMMENDED,
                    ),
                ],
                recommendations=[
                    AIRecommendation(
                        text="Create a reproducible deployment checklist.",
                        rationale=(
                            "A constrained environment benefits from explicit, repeatable "
                            "deployment steps even if the exact process is not yet defined."
                        ),
                    ),
                    AIRecommendation(
                        text="Document approved dependency sources.",
                        rationale=(
                            "The target environment may restrict public package access, so "
                            "dependency provenance should be recorded."
                        ),
                    ),
                ],
                subtask_revisions=subtask_revisions,
                acceptance_criteria_revisions=acceptance_criteria_revisions,
            )

        return AIReviewResult(
            suggested_title=normalized_title,
            suggested_description=(
                description
                or "Additional description is required to define the work."
            ),
            suggested_priority="medium",
            suggested_ticket_type="task",
            reasoning_summary=(
                "The ticket appears actionable but would benefit from "
                "clearer completion criteria and execution steps."
            ),
            missing_information=[
                "What does successful completion look like?",
                "Is there a required completion date?",
            ],
            acceptance_criteria=[
                AISuggestedAcceptanceCriterion(text="The requested work is completed.", basis=SuggestionBasis.INFERRED),
                AISuggestedAcceptanceCriterion(text="The result has been validated.", basis=SuggestionBasis.RECOMMENDED),
            ],
            suggested_subtasks=[
                AISuggestedSubtask(title="Clarify requirements", description="Confirm the expected outcome and constraints.", basis=SuggestionBasis.INFERRED),
                AISuggestedSubtask(title="Perform the work", description="Complete the primary work required by the ticket.", basis=SuggestionBasis.SUPPORTED),
                AISuggestedSubtask(title="Validate completion", description="Verify the result meets the expected outcome.", basis=SuggestionBasis.RECOMMENDED),
            ],
            recommendations=[
                AIRecommendation(
                    text="Add a concise definition of done.",
                    rationale=(
                        "The ticket would be easier to execute and validate with a clear "
                        "completion condition."
                    ),
                ),
            ],
            subtask_revisions=subtask_revisions,
            acceptance_criteria_revisions=acceptance_criteria_revisions,
        )

