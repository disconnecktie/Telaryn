// Protect report configuration, explicit evidence selection, and AI disclosure handoff.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import ReportsView from "./ReportsView";

const projects = [
  { id: 1, name: "Telaryn", life_context: "work", archived: false, included_by_default: true },
  { id: 2, name: "Community Event", life_context: "volunteer", archived: false, included_by_default: true },
  { id: 3, name: "Old Test", life_context: "work", archived: true, archive_reason: "test_development", included_by_default: false },
];

describe("Activity Reports", () => {
  test("defaults to eligible Work Projects and generates only after disclosure continuation", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue({
      title: "Weekly Activity Report",
      period_start: "2026-09-10",
      period_end: "2026-09-16",
      items: ["Advanced Telaryn through a reviewed release milestone."],
    });
    const onRequestAITransmission = vi.fn((continueGeneration) => continueGeneration());
    render(<ReportsView
      loadProjects={vi.fn().mockResolvedValue(projects)}
      onGenerate={onGenerate}
      onRequestAITransmission={onRequestAITransmission}
    />);

    await user.click(await screen.findByText("1 Project selected"));
    expect(screen.getByRole("checkbox", { name: /Telaryn/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Community Event/ })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Old Test/ })).not.toBeChecked();
    await user.click(screen.getByRole("button", { name: "Generate Activity Report" }));

    expect(onRequestAITransmission).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(onGenerate).toHaveBeenCalledWith({
      period: "weekly",
      output_format: "narrative",
      scope: "work",
      project_ids: [1],
      style_example: null,
      period_start: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
      period_end: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
    }));
    expect(await screen.findByText(/Advanced Telaryn/)).toBeInTheDocument();
  });

  test("changes the default selection when the life context changes", async () => {
    const user = userEvent.setup();
    render(<ReportsView
      loadProjects={vi.fn().mockResolvedValue(projects)}
      onGenerate={vi.fn()}
      onRequestAITransmission={vi.fn()}
    />);
    await user.click(await screen.findByText("1 Project selected"));
    await user.selectOptions(screen.getByLabelText("Life context"), "volunteer");
    expect(screen.getByRole("checkbox", { name: /Telaryn/ })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Community Event/ })).toBeChecked();
  });

  test("makes preset date boundaries explicit and editable", async () => {
    const user = userEvent.setup();
    render(<ReportsView
      loadProjects={vi.fn().mockResolvedValue(projects)}
      onGenerate={vi.fn()}
      onRequestAITransmission={vi.fn()}
    />);

    await screen.findByText("1 Project selected");
    const from = screen.getByLabelText("From");
    const through = screen.getByLabelText("Through");
    expect(from.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(through.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);

    await user.selectOptions(screen.getByLabelText("Period preset"), "monthly");
    expect(from.value.endsWith("-01")).toBe(true);

    await user.selectOptions(screen.getByLabelText("Period preset"), "annual");
    expect(screen.getByRole("option", { name: "Past 12 Months" })).toBeInTheDocument();
    const expected = new Date(`${through.value}T12:00:00`);
    expected.setDate(expected.getDate() + 1);
    expected.setFullYear(expected.getFullYear() - 1);
    expect(from.value).toBe([
      expected.getFullYear(),
      String(expected.getMonth() + 1).padStart(2, "0"),
      String(expected.getDate()).padStart(2, "0"),
    ].join("-"));
  });

  test("keeps optional style guidance collapsed and states the private-content boundary", async () => {
    const user = userEvent.setup();
    render(<ReportsView
      loadProjects={vi.fn().mockResolvedValue(projects)}
      onGenerate={vi.fn()}
      onRequestAITransmission={vi.fn()}
    />);

    expect(await screen.findByText(/Projects and Tickets marked Private/)).toBeInTheDocument();
    expect(screen.getByLabelText("Style example")).not.toBeVisible();
    await user.click(screen.getByText("Style example"));
    expect(screen.getByLabelText("Style example")).toBeVisible();
  });
});
