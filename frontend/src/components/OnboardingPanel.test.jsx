// Protects activity-derived progress presentation and explicit onboarding actions.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import OnboardingPanel from "./OnboardingPanel";

test("shows activity-derived progress and delegates explicit user actions", () => {
  const onAction = vi.fn();
  const onDismiss = vi.fn();
  const progress = { show_panel: true, completed: false, milestones: [
    { key: "capture", label: "Capture work", description: "Capture it.", completed: true },
    { key: "shape", label: "Refine and approve", description: "Shape it.", completed: false },
    { key: "focus", label: "Choose focus", description: "Focus it.", completed: false },
    { key: "record", label: "Record progress", description: "Record it.", completed: false },
  ] };
  render(<OnboardingPanel progress={progress} onAction={onAction} onGuide={vi.fn()} onDismiss={onDismiss} />);
  expect(screen.getByText("GETTING STARTED · 1 OF 4")).toBeInTheDocument();
  expect(screen.getAllByText("Done")).toHaveLength(1);
  expect(screen.getAllByText("Next")).toHaveLength(1);
  expect(screen.getAllByText("Later")).toHaveLength(2);
  expect(screen.queryByRole("button", { name: "Capture your first piece of work" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Choose what matters now" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Learn how to refine and approve" }));
  expect(onAction).toHaveBeenCalledWith("shape");
  fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
  expect(onDismiss).toHaveBeenCalledOnce();
});
