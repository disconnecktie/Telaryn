"""Import every ORM model so SQLAlchemy metadata and relationships are complete."""

from app.models.acceptance_criterion import AcceptanceCriterion
from app.models.access_request import AccessRequest, AccessRequestEvent, AccessRequestLimit
from app.models.account_admin_event import AccountAdminEvent
from app.models.feedback import FeedbackAdminEvent, FeedbackSubmission
from app.models.auth_session import AuthSession
from app.models.project import Project
from app.models.project_ai_policy_event import ProjectAIPolicyEvent
from app.models.project_lifecycle_event import ProjectLifecycleEvent
from app.models.project_review_attempt import ProjectReviewAttempt
from app.models.project_review_application import ProjectReviewApplication
from app.models.project_review_proposal_decision import ProjectReviewProposalDecision
from app.models.my_work_preference import MyWorkPreference
from app.models.onboarding_state import OnboardingState
from app.models.subtask import Subtask
from app.models.ticket import Ticket
from app.models.ticket_activity_event import TicketActivityEvent
from app.models.ticket_status_event import TicketStatusEvent
from app.models.ticket_update_attachment import TicketUpdateAttachment
from app.models.ticket_update_entry import TicketUpdateEntry
from app.models.ai_review import AIReview
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership
from app.models.work_intake_attempt import WorkIntakeAttempt
from app.models.workspace_invitation import WorkspaceInvitation, WorkspaceInvitationEvent

__all__ = [
    "WorkspaceInvitation",
    "AccountAdminEvent",
    "FeedbackAdminEvent",
    "FeedbackSubmission",
    "WorkspaceInvitationEvent",
    "AccessRequest",
    "AccessRequestEvent",
    "AccessRequestLimit",
    "AcceptanceCriterion",
    "AuthSession",
    "Project",
    "ProjectAIPolicyEvent",
    "ProjectLifecycleEvent",
    "ProjectReviewAttempt",
    "ProjectReviewApplication",
    "ProjectReviewProposalDecision",
    "MyWorkPreference",
    "Subtask",
    "Ticket",
    "TicketActivityEvent",
    "TicketStatusEvent",
    "TicketUpdateAttachment",
    "TicketUpdateEntry",
    "AIReview",
    "User",
    "Workspace",
    "WorkspaceMembership",
    "WorkIntakeAttempt",
]
