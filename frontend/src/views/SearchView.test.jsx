// Verifies debounced, filtered search presentation and result navigation.
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { searchWork } from "../api";
import SearchView from "./SearchView";

vi.mock("../api", () => ({ searchWork: vi.fn() }));

const empty = {
  projects: [],
  tickets: [],
  acceptance_criteria: [],
  subtasks: [],
  total: 0,
  truncated: false,
};

describe("SearchView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    searchWork.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("waits for two characters and debounces requests", async () => {
    searchWork.mockResolvedValue(empty);
    render(<SearchView onOpenResult={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "a" } });
    expect(screen.getByText("Enter at least two characters to search.")).toBeInTheDocument();
    expect(searchWork).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "atlas" } });
    expect(searchWork).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(searchWork).toHaveBeenCalledWith("atlas", {
      include_completed: false,
      include_cancelled: false,
      include_deferred: false,
      include_archived: false,
    });
  });

  test("groups contextual results and delegates result navigation", async () => {
    const onOpenResult = vi.fn();
    const ticket = {
      resource_type: "ticket",
      id: 49,
      reference: "TKT-049",
      title: "Search authorized Telaryn work",
      matched_field: "Ticket title",
      excerpt: "Search authorized Telaryn work",
      project_reference: "PRJ-001",
      project_name: "Telaryn Development",
      ticket_id: 49,
      ticket_reference: "TKT-049",
      status: "in_progress",
      archived: false,
      private: false,
      deferred: false,
    };
    searchWork.mockResolvedValue({ ...empty, tickets: [ticket], total: 1 });
    render(<SearchView onOpenResult={onOpenResult} />);

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "authorized" } });
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByRole("heading", { name: "Tickets" })).toBeInTheDocument();
    expect(screen.getByText("PRJ-001 · Telaryn Development · TKT-049")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /TKT-049/i }));
    expect(onOpenResult).toHaveBeenCalledWith(ticket);
  });

  test("reruns search when lifecycle filters change", async () => {
    searchWork.mockResolvedValue(empty);
    render(<SearchView onOpenResult={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "migration" } });
    await act(() => vi.advanceTimersByTimeAsync(300));
    fireEvent.click(screen.getByLabelText("Archived Projects"));
    await act(() => vi.advanceTimersByTimeAsync(300));

    expect(searchWork).toHaveBeenLastCalledWith("migration", expect.objectContaining({
      include_archived: true,
    }));
  });

  test("shows safe empty and failure states", async () => {
    searchWork.mockResolvedValueOnce(empty).mockRejectedValueOnce(new Error("Search unavailable."));
    render(<SearchView onOpenResult={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "nothing" } });
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByText("No matching work found.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search Telaryn"), { target: { value: "failure" } });
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(screen.getByRole("alert")).toHaveTextContent("Search unavailable.");
  });
});

