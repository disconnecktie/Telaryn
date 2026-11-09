// Protects project ranking and bounded navigator interactions as the Projects workspace evolves.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import ProjectNavigator from "./ProjectNavigator";
import { rankProjectSummaries } from "./projectRanking";

const projects = [
  { id: 1, name: "Telaryn Development", target_date: null },
  { id: 2, name: "House Projects", target_date: "2026-09-01" },
  { id: 3, name: "Career Transition", target_date: null },
];

describe("ProjectNavigator", () => {
  test("keeps ranking explainable and stable", () => {
    const ranked = rankProjectSummaries({
      projects,
      tickets: [
        {
          id: 10,
          project_id: 3,
          status: "in_progress",
          updated_at: "2026-08-27T12:00:00Z",
        },
        { id: 11, project_id: 2, status: "active" },
      ],
      preferredProjectId: 1,
      currentFocusProjectId: 3,
      now: new Date("2026-08-28T12:00:00Z"),
    });

    expect(ranked.map((project) => project.id)).toEqual([1, 3, 2]);
    expect(ranked.map((project) => project.reason)).toEqual([
      "Default project",
      "Current Focus",
      "Due soon",
    ]);
  });

  test("filters authorized project names and selects from the bounded navigator", async () => {
    const user = userEvent.setup();
    const onSelectProject = vi.fn();

    render(
      <ProjectNavigator
        projects={projects}
        tickets={[]}
        selectedProjectId={1}
        preferredProjectId={1}
        currentFocusProjectId={null}
        unassignedTickets={[]}
        onSelectProject={onSelectProject}
        onCreateProject={vi.fn()}
      />,
    );

    const navigator = screen.getByRole("complementary", {
      name: "Project Navigator",
    });
    expect(
      within(navigator).getByRole("button", { name: /Telaryn Development/ }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(within(navigator).getByText("Default project"))
      .toHaveClass("project-default-badge");

    await user.type(screen.getByRole("searchbox", { name: "Filter projects" }), "house");
    expect(
      within(navigator).getByRole("button", { name: /House Projects/ }),
    ).toBeInTheDocument();
    expect(
      within(navigator).queryByRole("button", { name: /Career Transition/ }),
    ).not.toBeInTheDocument();

    await user.click(
      within(navigator).getByRole("button", { name: /House Projects/ }),
    );
    expect(onSelectProject).toHaveBeenCalledWith(2);
  });

});

