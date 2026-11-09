// Protect the focused My Work interactions without depending on App orchestration.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import MyWorkView from "./MyWorkView";

beforeEach(() => {
  window.localStorage.clear();
});

function item(overrides = {}) {
  return {
    id: 47,
    workspace_ticket_number: 47,
    title: "Build the focus stack",
    project_id: 1,
    project_name: "Telaryn Development",
    project_purpose: "Make work easier to resume.",
    project_why_it_matters: "Reduce the effort of deciding what to do next.",
    project_target_date: "2026-11-01",
    focus_rationale: "The ticket is ready to begin. It addresses: Make work easier to resume. Remaining scope: 2 of 3 acceptance criteria and 2 of 2 subtasks.",
    status: "ready",
    priority: "high",
    updated_at: "2026-08-27T12:00:00Z",
    reasons: ["Ready to begin"],
    acceptance_criteria: { completed: 1, total: 3 },
    subtasks: { completed: 0, total: 2 },
    next_action: { subtask_id: 9, title: "Persist current focus", status: "todo" },
    availability_mode: "available",
    available_on: null,
    ...overrides,
  };
}

function props(work) {
  return {
    work,
    loading: false,
    error: null,
    canUndoFocus: false,
    onOpenTicket: vi.fn(),
    onSetFocus: vi.fn(),
    onUndoFocus: vi.fn(),
    onSetAvailability: vi.fn(),
    onMakeAvailable: vi.fn(),
    onCompleteNextAction: vi.fn(),
    onStartGuidedIntake: vi.fn(),
    onRefineGuidedIntake: vi.fn(),
    onRecoverGuidedIntake: vi.fn().mockResolvedValue(null),
    onGetGuidedIntake: vi.fn(),
    onCancelGuidedIntake: vi.fn(),
    onDismissGuidedIntake: vi.fn().mockResolvedValue(null),
    onContinueGuidedIntake: vi.fn(),
  };
}

describe("MyWorkView", () => {
  test("formats machine-like Current Focus tokens with semantic break opportunities", () => {
    const viewProps = props({
      current_focus: item({
        focus_rationale: "Configure ATLAS_DEPLOYMENT_ADMINISTRATOR_IDS before release.",
        next_action: {
          subtask_id: 9,
          title: "Use ATLAS_FEEDBACK_REVIEWER_IDS for reviewer access",
          status: "todo",
        },
      }),
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });

    const { container } = render(<MyWorkView {...viewProps} />);

    const tokens = [...container.querySelectorAll(".my-work-technical-token")];
    expect(tokens.map((token) => token.textContent)).toEqual([
      "ATLAS_DEPLOYMENT_ADMINISTRATOR_IDS",
      "ATLAS_FEEDBACK_REVIEWER_IDS",
    ]);
    expect(tokens.every((token) => token.querySelectorAll("wbr").length >= 2)).toBe(true);
  });

  test("makes Capture Work the primary card for a workspace with no work", () => {
    const viewProps = props({
      current_focus: null,
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });

    render(<MyWorkView {...viewProps} />);

    const intake = screen
      .getByRole("textbox", { name: "What needs to get done?" })
      .closest(".my-work-guided-intake");
    expect(intake).toHaveClass("is-prominent", "is-expanded");
    expect(intake.nextElementSibling).toHaveClass("my-work-current-focus");
    expect(screen.queryByRole("button", { name: "Capture New Work" })).not.toBeInTheDocument();
  });

  test("keeps intake inline until the user continues with the proposal", async () => {
    const user = userEvent.setup();
    const viewProps = props({
      current_focus: item(),
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    viewProps.onStartGuidedIntake.mockResolvedValue({
      id: 12,
      source_text: "Turn this email into a concrete delivery plan.",
      status: "completed",
      result: {
      action: "create_ticket",
      summary: "Add document intake as one bounded Ticket.",
      rationale: "The request describes one deliverable.",
      confidence: "high",
      target_project_id: 1,
      target_ticket_id: null,
      matched_projects: [{ id: 1, reference: "PRJ-001", name: "Telaryn Development" }],
      matched_tickets: [],
      proposed_project: null,
      proposed_tickets: [{
        title: "Add document intake",
        description: "Shape uploaded source material into proposed work.",
        priority: "medium",
        ticket_type: "development",
        project_id: 1,
        acceptance_criteria: [{
          text: "The source produces a reviewable delivery plan.",
          basis: "supported",
        }],
        subtasks: [{
          text: "Confirm the source and expected outcome.",
          basis: "inferred",
        }],
      }],
      proposed_ticket_changes: null,
      questions: [],
      },
    });
    render(<MyWorkView {...viewProps} />);

    const suggestedNext = screen.getByRole("heading", { name: "Other meaningful options" });
    const captureWork = screen.getByRole("button", { name: "Capture New Work" });
    expect(suggestedNext.closest("section").nextElementSibling).toContainElement(
      captureWork,
    );
    expect(screen.queryByRole("textbox", { name: "What needs to get done?" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Capture New Work" }));

    await user.type(
      screen.getByRole("textbox", { name: "What needs to get done?" }),
      "  Turn this email into a concrete delivery plan.  ",
    );
    await user.click(screen.getByRole("button", { name: "Shape with Telaryn" }));

    expect(viewProps.onStartGuidedIntake).not.toHaveBeenCalled();
    expect(
      screen.getByRole("dialog", { name: "Before you continue" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continue with AI" }));

    expect(viewProps.onStartGuidedIntake).toHaveBeenCalledWith(
      "Turn this email into a concrete delivery plan.",
      { signal: expect.any(AbortSignal) },
    );
    expect(await screen.findByText("Add document intake as one bounded Ticket.")).toBeInTheDocument();
    expect(viewProps.onContinueGuidedIntake).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Collapse" }));
    expect(screen.getByRole("status")).toHaveTextContent("Proposal ready");
    expect(screen.getByRole("heading", { name: "Add document intake as one bounded Ticket." })).toBeInTheDocument();
    expect(screen.getByText("Nothing has been created yet.", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Capture New Work" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Review Proposal" }));

    await user.click(screen.getByText("Proposed plan"));
    expect(screen.getByText("1 outcome · 1 step")).toBeInTheDocument();
    expect(screen.getByText("Done looks like")).toBeInTheDocument();
    expect(screen.getByText("Steps to take")).toBeInTheDocument();
    expect(screen.getByText("The source produces a reviewable delivery plan.")).toBeInTheDocument();
    expect(screen.getByText("Confirm the source and expected outcome.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Continue to Ticket Draft" }));
    await waitFor(() => {
      expect(viewProps.onDismissGuidedIntake).toHaveBeenCalledWith(12);
      expect(viewProps.onContinueGuidedIntake).toHaveBeenCalledWith(
        "Turn this email into a concrete delivery plan.",
        expect.objectContaining({ action: "create_ticket" }),
        0,
      );
    });
  });

  test("answers focused questions and queues one refinement without blocking continuation", async () => {
    const user = userEvent.setup();
    const viewProps = props({
      current_focus: item(), suggestions: [], upcoming: [], ready_later_count: 0,
      needs_attention: [], in_review: [], recently_completed: [],
    });
    const proposal = {
      action: "create_ticket",
      summary: "Draft an onboarding plan.",
      rationale: "The request describes one deliverable.",
      confidence: "medium",
      target_project_id: null,
      target_ticket_id: null,
      matched_projects: [],
      matched_tickets: [],
      proposed_project: null,
      proposed_tickets: [{
        title: "Plan onboarding", description: "Prepare a reviewable plan.",
        priority: "medium", ticket_type: "task", project_id: null,
        acceptance_criteria: [{ text: "The plan names an approver.", basis: "recommended" }],
        subtasks: [{ text: "Draft the plan.", basis: "supported" }],
      }],
      proposed_ticket_changes: null,
      questions: [
        "Who should approve the completed plan?",
        "When does the plan need to be ready?",
      ],
      is_provisional: true,
      clarification_prompt: "One answer can make this plan more specific.",
    };
    viewProps.onRecoverGuidedIntake.mockResolvedValue({
      id: 44, source_text: "Plan onboarding", status: "completed",
      result: proposal, clarification_answers: [], refinement_count: 0,
    });
    viewProps.onRefineGuidedIntake.mockResolvedValue({
      id: 44, source_text: "Plan onboarding", status: "pending",
      result: proposal, clarification_answers: ["The operations lead"], refinement_count: 1,
    });

    render(<MyWorkView {...viewProps} />);
    expect(await screen.findByText("Built from the context available")).toBeInTheDocument();
    expect(screen.getAllByRole("textbox")).toHaveLength(2);
    const answer = screen.getByRole("textbox", { name: "Who should approve the completed plan?" });
    await user.type(answer, "The operations lead");
    await user.click(screen.getByRole("button", { name: "Refine Proposal" }));
    expect(viewProps.onRefineGuidedIntake).toHaveBeenCalledWith(44, ["The operations lead"]);
    expect(screen.getByText(/refining this proposal with your answers/i)).toBeInTheDocument();
    expect(screen.getByText("Draft an onboarding plan.")).toBeInTheDocument();
  });

  test("recovers a completed Capture Work operation after remount", async () => {
    const viewProps = props({
      current_focus: item(),
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    viewProps.onRecoverGuidedIntake.mockResolvedValue({
      id: 18,
      source_text: "Plan a new onboarding workflow.",
      status: "completed",
      result: {
        action: "create_project",
        summary: "Create an onboarding project.",
        rationale: "The work contains multiple coordinated deliverables.",
        confidence: "high",
        target_project_id: null,
        target_ticket_id: null,
        matched_projects: [],
        matched_tickets: [],
        proposed_project: { name: "Employee Onboarding" },
        proposed_tickets: [{
          title: "Define the onboarding checklist",
          acceptance_criteria: ["The checklist covers required access and training."],
          subtasks: ["Interview the hiring manager."],
        }],
        proposed_ticket_changes: null,
        questions: [],
      },
    });

    render(<MyWorkView {...viewProps} />);

    expect(await screen.findByText("Create an onboarding project.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "What needs to get done?" })).not.toBeInTheDocument();
  });

  test("lets the user choose focus without opening the ticket drawer", async () => {
    const user = userEvent.setup();
    const suggestion = item();
    const viewProps = props({
      current_focus: null,
      suggestions: [suggestion],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    render(<MyWorkView {...viewProps} />);

    await user.click(screen.getByRole("button", { name: "Focus This" }));

    expect(viewProps.onSetFocus).toHaveBeenCalledWith(suggestion);
    expect(viewProps.onOpenTicket).not.toHaveBeenCalled();
  });

  test("shows the stable ticket reference with Current Focus project metadata", () => {
    const focus = item();
    render(<MyWorkView {...props({
      current_focus: focus,
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    })} />);

    expect(screen.getByText("TKT-047")).toBeInTheDocument();
    expect(screen.getByText("Telaryn Development")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Build the focus stack" })).toBeInTheDocument();
  });

  test("presents ticket-specific rationale without generic Project context", () => {
    const focus = item();
    render(<MyWorkView {...props({
      current_focus: focus, suggestions: [], upcoming: [], ready_later_count: 0,
      needs_attention: [], in_review: [], recently_completed: [],
    })} />);

    expect(screen.getByText("Why this ticket now")).toBeInTheDocument();
    expect(screen.getByText(focus.focus_rationale)).toBeInTheDocument();
    expect(screen.queryByText("Project context")).not.toBeInTheDocument();
    expect(screen.queryByText(focus.project_why_it_matters)).not.toBeInTheDocument();
  });

  test("stages the next action through the parent reviewed workflow", async () => {
    const user = userEvent.setup();
    const focus = item({ status: "in_progress" });
    const viewProps = props({
      current_focus: focus,
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    render(<MyWorkView {...viewProps} />);

    await user.click(screen.getByRole("button", { name: "Mark Complete" }));

    expect(viewProps.onCompleteNextAction).toHaveBeenCalledWith(focus);
  });

  test("explains missing next action without showing an unavailable AI control", async () => {
    const user = userEvent.setup();
    const focus = item({ next_action: null });
    const viewProps = props({
      current_focus: focus,
      suggestions: [],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    render(<MyWorkView {...viewProps} />);

    expect(screen.getByRole("heading", { name: "No unfinished subtask is available." })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ask Telaryn for a Next Step" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open Ticket to Add One" }));
    expect(viewProps.onOpenTicket).toHaveBeenCalledWith(focus);
  });

  test("removes a suggestion until the user-selected availability condition", async () => {
    const user = userEvent.setup();
    const suggestion = item();
    const viewProps = props({
      current_focus: null,
      suggestions: [suggestion],
      upcoming: [],
      ready_later_count: 0,
      needs_attention: [],
      in_review: [],
      recently_completed: [],
    });
    render(<MyWorkView {...viewProps} />);

    await user.click(screen.getByRole("button", { name: "Not Now" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Available for Focus" }), "context_change");
    await user.click(screen.getByRole("button", { name: "Set Availability" }));

    expect(viewProps.onSetAvailability).toHaveBeenCalledWith(
      suggestion,
      "context_change",
      null,
    );
  });
});

test("keeps Undo feedback inside Current Focus and hides it when not enabled", async () => {
  const viewProps = props({
    current_focus: item(), suggestions: [], upcoming: [],
    ready_later_count: 0, needs_attention: [], in_review: [], recently_completed: [],
  });
  const user = userEvent.setup();
  const { rerender } = render(<MyWorkView {...viewProps} canUndoFocus />);
  const notice = screen.getByRole("status");
  expect(notice.closest(".my-work-current-focus")).not.toBeNull();
  await user.click(screen.getByRole("button", { name: "Undo" }));
  expect(viewProps.onUndoFocus).toHaveBeenCalledTimes(1);
  rerender(<MyWorkView {...viewProps} />);
  expect(screen.queryByText("Current Focus changed.")).not.toBeInTheDocument();
});
