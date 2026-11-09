// Verifies temporary Current Focus ordering without mutating visible ticket results.
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProjectNavigator from "../components/projects/ProjectNavigator";
import { pinCurrentFocusTicket } from "./focusTicketOrdering";

const tickets = [
  { id: 10, title: "First" },
  { id: 20, title: "Focused" },
  { id: 30, title: "Third" },
];

describe("pinCurrentFocusTicket", () => {
  it("moves Current Focus to the front without duplicating it", () => {
    const ordered = pinCurrentFocusTicket(tickets, 20);

    expect(ordered.map((ticket) => ticket.id)).toEqual([20, 10, 30]);
    expect(ordered.filter((ticket) => ticket.id === 20)).toHaveLength(1);
  });

  it("preserves the existing order of every other ticket", () => {
    const ordered = pinCurrentFocusTicket(tickets, 30);

    expect(ordered.map((ticket) => ticket.id)).toEqual([30, 10, 20]);
  });

  it("does not insert a focused ticket excluded by the visible result set", () => {
    const visibleTickets = tickets.filter((ticket) => ticket.id !== 20);
    const ordered = pinCurrentFocusTicket(visibleTickets, 20);

    expect(ordered).toBe(visibleTickets);
    expect(ordered.map((ticket) => ticket.id)).toEqual([10, 30]);
  });

  it("leaves results unchanged when Current Focus is already first or absent", () => {
    expect(pinCurrentFocusTicket(tickets, 10)).toBe(tickets);
    expect(pinCurrentFocusTicket(tickets, null)).toBe(tickets);
  });
});


describe("ProjectNavigator lifecycle collections", () => {
  const activeProject = {
    id: 1, workspace_project_number: 1, name: "Active Project",
    target_date: null, ai_context_enabled: true,
  };
  const archivedProject = {
    id: 2, workspace_project_number: 2, name: "Preserved Project",
    target_date: null, ai_context_enabled: true, archived_at: "2026-09-13T08:00:00Z",
    archive_reason: "superseded",
  };

  it("keeps archived Projects behind an intentional navigator choice", () => {
    const onSelectProject = vi.fn();
    render(
      <ProjectNavigator
        projects={[activeProject]}
        archivedProjects={[archivedProject]}
        tickets={[]}
        archivedTickets={[]}
        selectedProjectId={null}
        preferredProjectId={null}
        currentFocusProjectId={null}
        unassignedTickets={[]}
        onSelectProject={onSelectProject}
        onCreateProject={() => {}}
      />,
    );

    expect(screen.getByText(/Active Project/)).toBeInTheDocument();
    expect(screen.queryByText(/Preserved Project/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Archived 1/ }));
    expect(onSelectProject).toHaveBeenCalledWith(null);
    expect(screen.getByText(/Preserved Project/)).toBeInTheDocument();

    expect(screen.getByText("Show archive reasons")).toBeInTheDocument();
    expect(screen.getByText("All")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Show archive reasons"));
    expect(screen.getAllByText("Superseded")).toHaveLength(2);
    fireEvent.click(screen.getByRole("checkbox", { name: "Superseded" }));
    expect(screen.queryByText(/Preserved Project/)).not.toBeInTheDocument();
    expect(screen.getByText("No archived Projects match the selected reasons.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Superseded" }));
    fireEvent.click(screen.getByRole("button", { name: /Preserved Project/ }));
    expect(onSelectProject).toHaveBeenLastCalledWith(2);
  });
});


describe("ProjectNavigator collection switching", () => {
  it("opens the lifecycle collection containing the selected Project", () => {
    const onSelectProject = vi.fn();
    render(
      <ProjectNavigator
        projects={[{
          id: 1, workspace_project_number: 1, name: "Active Project",
          target_date: null, ai_context_enabled: true,
        }]}
        archivedProjects={[{
          id: 2, workspace_project_number: 2, name: "Archived Project",
          target_date: null, ai_context_enabled: true, archived_at: "2026-09-13T08:00:00Z",
        }]}
        tickets={[]}
        archivedTickets={[]}
        selectedProjectId={2}
        preferredProjectId={null}
        currentFocusProjectId={null}
        unassignedTickets={[]}
        onSelectProject={onSelectProject}
        onCreateProject={() => {}}
      />,
    );

    expect(screen.getByText(/Archived Project/)).toBeInTheDocument();
    expect(screen.queryByText(/Active Project/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Archived 1/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(onSelectProject).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Active" }));
    expect(onSelectProject).toHaveBeenLastCalledWith(null);
  });
});
