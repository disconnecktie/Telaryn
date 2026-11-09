"""Describe the explicit work context Telaryn is allowed to send to AI providers."""

from dataclasses import dataclass, field


@dataclass
class SubtaskContext:
    title: str
    description: str | None
    status: str
    completed: bool


@dataclass
class AcceptanceCriterionContext:
    text: str
    completed: bool


@dataclass
class WorkContext:
    """The explicit, minimal work bundle an AI provider may review.

    It describes current work for analysis only; it does not authorize a provider
    to change a ticket or any related record.
    """
    title: str
    description: str | None
    project_name: str | None
    status: str
    priority: str
    ticket_type: str
    subtasks: list[SubtaskContext] = field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterionContext] = field(
        default_factory=list
    )

