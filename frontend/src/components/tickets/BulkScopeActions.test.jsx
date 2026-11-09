// Verifies section-level bulk controls appear only for meaningful remaining scope.
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AcceptanceCriteriaSection from "./AcceptanceCriteriaSection";
import SubtasksSection from "./SubtasksSection";

describe("bulk scope completion controls", () => {
  it("offers Acceptance Criteria bulk completion for at least two active items", () => {
    const onCompleteRemaining = vi.fn();
    render(
      <AcceptanceCriteriaSection
        criteria={[
          { id: 1, text: "First", completed: false, deferred: false },
          { id: 2, text: "Second", completed: false, deferred: false },
          { id: 3, text: "Deferred", completed: false, deferred: true },
        ]}
        editCriteria={[]}
        editing={false}
        editingKey={null}
        loading={false}
        error={null}
        canEdit={false}
        newCriterionText=""
        onCompleteRemaining={onCompleteRemaining}
        onToggleCompleted={vi.fn()}
        onToggleDeferred={vi.fn()}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Complete all remaining acceptance criteria",
      }),
    );
    expect(onCompleteRemaining).toHaveBeenCalledOnce();
  });

  it("does not offer Criteria bulk completion for one remaining item", () => {
    render(
      <AcceptanceCriteriaSection
        criteria={[
          { id: 1, text: "First", completed: false, deferred: false },
          { id: 2, text: "Done", completed: true, deferred: false },
        ]}
        editCriteria={[]}
        editing={false}
        editingKey={null}
        loading={false}
        error={null}
        canEdit={false}
        newCriterionText=""
        onCompleteRemaining={vi.fn()}
        onToggleCompleted={vi.fn()}
        onToggleDeferred={vi.fn()}
      />,
    );

    expect(
      screen.queryByRole("button", {
        name: "Complete all remaining acceptance criteria",
      }),
    ).not.toBeInTheDocument();
  });

  it("offers Subtask bulk completion while excluding deferred work", () => {
    const onCompleteRemaining = vi.fn();
    render(
      <SubtasksSection
        subtasks={[
          { id: 1, title: "First", status: "todo" },
          { id: 2, title: "Second", status: "in_progress" },
          { id: 3, title: "Deferred", status: "deferred" },
        ]}
        editSubtasks={[]}
        editing={false}
        editingKey={null}
        loading={false}
        error={null}
        canEdit={false}
        onCompleteRemaining={onCompleteRemaining}
        onToggleCompleted={vi.fn()}
        onToggleDeferred={vi.fn()}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Complete all remaining subtasks",
      }),
    );
    expect(onCompleteRemaining).toHaveBeenCalledOnce();
  });
});
