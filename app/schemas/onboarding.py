"""API contracts for the activity-derived first-run guide."""

from pydantic import BaseModel, ConfigDict


class OnboardingMilestone(BaseModel):
    key: str
    label: str
    description: str
    completed: bool


class OnboardingProgress(BaseModel):
    dismissed: bool
    completed: bool
    show_panel: bool
    milestones: list[OnboardingMilestone]


class OnboardingVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dismissed: bool
