// Protects explicit generation, freshness, evidence, and advisory-only Project Review behavior.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import {
  applyProjectReview,
  createProjectReview,
  getProjectReviewApplicationPreview,
  getProjectReviewContext,
  getProjectReviewDecisions,
  getProjectReviews,
  saveProjectReviewDecision,
} from "../../api";
import ProjectReviewPanel from "./ProjectReviewPanel";

vi.mock("../../api", () => ({
  applyProjectReview: vi.fn(),
  createProjectReview: vi.fn(),
  getProjectReviewApplicationPreview: vi.fn(),
  getProjectReviewContext: vi.fn(),
  getProjectReviewDecisions: vi.fn(),
  makeProjectReviewFocus: vi.fn(),
  getProjectReviews: vi.fn(),
  saveProjectReviewDecision: vi.fn(),
  undoProjectReviewFocus: vi.fn(),
}));

const project = { id: 1, name: "Telaryn Development" };
const tickets = [
  { id: 41, title: "Build Human-Governed Telaryn Project Review" },
  { id: 40, title: "Establish Secure Deployment" },
];

const emptyChanges = {
  title: null,
  description: null,
  priority: null,
  ticket_type: null,
  acceptance_criteria: [],
  subtasks: [],
  project_description: null,
  project_purpose: null,
  project_why_it_matters: null,
  project_target_date: null,
};

const completedReview = {
  id: 9,
  project_id: 1,
  snapshot_version: "snapshot-current",
  status: "completed",
  provider: "mock",
  model: "deterministic",
  safe_error_category: null,
  duration_ms: 50,
  created_at: "2026-08-28T08:00:00Z",
  completed_at: "2026-08-28T08:00:01Z",
  result: {
    outcome: "changes_proposed",
    summary: "The project is healthy, but deployment work needs a clearer boundary.",
    findings: [
      {
        summary: "Active work is defined and moving.",
        basis: "supported",
        significance: "important",
        evidence: [
          {
            source_type: "ticket",
            source_id: 41,
            field_name: null,
            summary: "Project Review has a concrete active implementation ticket.",
          },
        ],
      },
    ],
    risks: [
      {
        summary: "Deployment remains underspecified.",
        basis: "inferred",
        significance: "necessary",
        evidence: [
          {
            source_type: "ticket",
            source_id: 40,
            field_name: "description",
            summary: "The deployment ticket does not yet select an environment.",
          },
        ],
      },
    ],
    planning_guidance: [
      {
        summary: "Finish the bounded Project Review presentation first.",
        basis: "recommended",
        evidence: [],
      },
    ],
    proposals: [
      {
        proposal_type: "add_subtasks",
        summary: "Add a staging-environment decision.",
        basis: "recommended",
        significance: "important",
        evidence: [
          {
            source_type: "ticket",
            source_id: 40,
            field_name: "description",
            summary: "The deployment boundary is still open.",
          },
        ],
        target_project_id: null,
        target_ticket_id: 40,
        proposed_changes: {
          ...emptyChanges,
          subtasks: ["Select the initial staging environment"],
        },
      },
    ],
    recommended_focus: {
      ticket_id: 41,
      rationale: "This is the smallest useful next slice.",
      basis: "recommended",
      evidence: [
        {
          source_type: "ticket",
          source_id: 41,
          field_name: null,
          summary: "The backend review boundary is already complete.",
        },
      ],
    },
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  getProjectReviewContext.mockResolvedValue({
    snapshot_version: "snapshot-current",
  });
  getProjectReviews.mockResolvedValue([]);
  getProjectReviewDecisions.mockResolvedValue([]);
  saveProjectReviewDecision.mockImplementation((projectId, reviewId, proposalIndex, value) =>
    Promise.resolve({
      proposal_index: proposalIndex,
      ...value,
      created_at: "2026-08-28T08:00:00Z",
      updated_at: "2026-08-28T08:00:00Z",
    }),
  );
  getProjectReviewApplicationPreview.mockResolvedValue({
    review_id: 9,
    items: [{
      proposal_index: 0,
      proposal_type: "add_subtasks",
      summary: "Add a staging-environment decision.",
      target_project_id: null,
      target_ticket_id: 40,
      candidate_changes: { ...emptyChanges, subtasks: ["Select the initial staging environment"] },
    }],
    conflicts: [],
    can_apply: true,
  });
  applyProjectReview.mockResolvedValue({
    id: 3,
    review_id: 9,
    proposal_indexes: [0],
    resulting_changes: [],
    applied_at: "2026-08-29T08:00:00Z",
  });
  createProjectReview.mockResolvedValue(completedReview);
});

test("generates and presents a read-only review with human-readable evidence", async () => {
  const user = userEvent.setup();
  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Review Project with Telaryn" }),
  );
  expect(createProjectReview).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Continue with AI" }));

  await vi.waitFor(() => {
    expect(createProjectReview).toHaveBeenCalledWith(1, { forceFresh: false });
  }, { timeout: 3000 });
  expect(
    await screen.findByRole("heading", { name: "Project Review" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Current snapshot")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", {
      name: "Build Human-Governed Telaryn Project Review",
    }),
  ).toBeInTheDocument();
  expect(screen.getByText("Add a staging-environment decision.")).toBeInTheDocument();
  expect(
    screen.getByText("Telaryn has not changed your project."),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Approval alone changes nothing/),
  ).toBeInTheDocument();

  await user.click(screen.getAllByText("Why Telaryn thinks this")[0]);
  expect(
    screen.getByText("The backend review boundary is already complete."),
  ).toBeInTheDocument();
});

test("cancels the external AI disclosure without starting a review", async () => {
  const user = userEvent.setup();
  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Review Project with Telaryn" }),
  );
  await user.click(screen.getByRole("button", { name: "Cancel" }));

  expect(createProjectReview).not.toHaveBeenCalled();
});

test("marks an older review stale without generating another review", async () => {
  getProjectReviews.mockResolvedValue([
    { ...completedReview, snapshot_version: "snapshot-older" },
  ]);

  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  expect(await screen.findByText("Project changed")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Telaryn Project Review" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      "The project is healthy, but deployment work needs a clearer boundary.",
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Open Full Review" }),
  ).toBeInTheDocument();
  expect(createProjectReview).not.toHaveBeenCalled();
});

test("confirms before queueing a fresh unchanged review", async () => {
  const user = userEvent.setup();
  window.confirm = vi.fn(() => true);
  getProjectReviews.mockResolvedValue([completedReview]);
  createProjectReview.mockResolvedValueOnce({
    ...completedReview,
    id: 10,
    status: "pending",
    completed_at: null,
    result: null,
  });

  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Review Again" }),
  );
  await user.click(screen.getByRole("button", { name: "Continue with AI" }));

  expect(window.confirm).toHaveBeenCalledWith(
    expect.stringContaining("Run a new review anyway?"),
  );
  await vi.waitFor(() => {
    expect(createProjectReview).toHaveBeenCalledWith(1, { forceFresh: true });
  }, { timeout: 3000 });
  expect(
    await screen.findByText(/Telaryn queued a full review of the current snapshot/),
  ).toBeInTheDocument();
});


test("persists approval without claiming the proposal was applied", async () => {
  const user = userEvent.setup();
  getProjectReviews.mockResolvedValue([completedReview]);

  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  await user.click(await screen.findByRole("button", { name: "Open Full Review" }));
  await user.click(screen.getByRole("button", { name: "Approve" }));

  expect(saveProjectReviewDecision).toHaveBeenCalledWith(
    1,
    9,
    0,
    expect.objectContaining({ decision: "approved" }),
  );
  const approvedState = await screen.findByText(/Approved · Not applied/);
  expect(approvedState).toBeInTheDocument();
  expect(within(approvedState).getByRole("button", { name: "Undo" })).toBeInTheDocument();
  const selectedApprove = screen.getByRole("button", { name: "Approve" });
  expect(selectedApprove).toBeDisabled();
  await user.click(selectedApprove);
  expect(saveProjectReviewDecision).toHaveBeenCalledTimes(1);
  expect(
    screen.getByText(/Project and Ticket changes use the reviewed atomic application above/),
  ).toBeInTheDocument();
});

test("locks decisions when the selected review is stale", async () => {
  const user = userEvent.setup();
  getProjectReviews.mockResolvedValue([
    { ...completedReview, snapshot_version: "snapshot-older" },
  ]);

  render(
    <ProjectReviewPanel
      project={project}
      tickets={tickets}
      onOpenTicket={vi.fn()}
    />,
  );

  await user.click(await screen.findByRole("button", { name: "Open Full Review" }));
  expect(
    screen.getByText("Review Again to make decisions on current project data."),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
});


test("previews and atomically applies approved candidates", async () => {
  const user = userEvent.setup();
  getProjectReviews.mockResolvedValue([completedReview]);
  getProjectReviewDecisions
    .mockResolvedValueOnce([{
      proposal_index: 0,
      decision: "approved",
      edited_changes: null,
      note: null,
      application_id: null,
      created_at: "2026-08-29T08:00:00Z",
      updated_at: "2026-08-29T08:00:00Z",
    }])
    .mockResolvedValueOnce([{
      proposal_index: 0,
      decision: "approved",
      edited_changes: null,
      note: null,
      application_id: 3,
      created_at: "2026-08-29T08:00:00Z",
      updated_at: "2026-08-29T08:01:00Z",
    }]);

  render(<ProjectReviewPanel project={project} tickets={tickets} onOpenTicket={vi.fn()} />);
  await user.click(await screen.findByRole("button", { name: "Open Full Review" }));
  await user.click(await screen.findByRole("button", { name: "Review Approved Changes" }));
  expect(await screen.findByRole("heading", { name: "Final approved-change summary" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Apply 1 Approved Change" }));

  expect(applyProjectReview).toHaveBeenCalledWith(1, 9);
  expect(await screen.findByText("Applied")).toBeInTheDocument();
  expect(screen.getByText(/Ticket status and Current Focus were unchanged/)).toBeInTheDocument();
});

