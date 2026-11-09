// Keep description disclosure local to Ticket Details and independent of drawer orchestration.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";

import TicketDetailsSection from "./TicketDetailsSection";


function ticket(overrides = {}) {
  return {
    id: 52,
    title: "Collapse long descriptions",
    description: "A sufficiently detailed ticket description ".repeat(20),
    priority: "medium",
    status: "in_progress",
    ticket_type: "task",
    project_id: 1,
    ...overrides,
  };
}

function props(currentTicket, overrides = {}) {
  return {
    ticket: currentTicket,
    projects: [{ id: 1, name: "Telaryn Development" }],
    projectName: "Telaryn Development",
    editing: false,
    editForm: { ...currentTicket },
    canEdit: true,
    onStartEditing: vi.fn(),
    onEditFieldChange: vi.fn(),
    onFocus: vi.fn(),
    onMakeAvailableAndFocus: vi.fn(),
    onUndoFocus: vi.fn(),
    ...overrides,
  };
}

function mockDescriptionMeasurements({ scrollHeight, clientHeight }) {
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(scrollHeight);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(clientHeight);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TicketDetailsSection description disclosure", () => {
  test("expands and collapses a rendered description that overflows", async () => {
    const user = userEvent.setup();
    mockDescriptionMeasurements({ scrollHeight: 160, clientHeight: 80 });
    render(<TicketDetailsSection {...props(ticket())} />);

    const description = screen.getByText(/A sufficiently detailed ticket description/);
    const expand = screen.getByRole("button", { name: "Read More" });
    expect(description).toHaveClass("collapsed");
    expect(expand).toHaveAttribute("aria-expanded", "false");

    await user.click(expand);

    expect(description).toHaveClass("expanded");
    expect(screen.getByRole("button", { name: "Show Less" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    await user.click(screen.getByRole("button", { name: "Show Less" }));
    expect(description).toHaveClass("collapsed");
  });

  test("does not show a disclosure control for a short description", () => {
    mockDescriptionMeasurements({ scrollHeight: 64, clientHeight: 64 });
    render(
      <TicketDetailsSection
        {...props(ticket({ description: "Short and useful." }))}
      />,
    );

    expect(screen.queryByRole("button", { name: "Read More" })).not.toBeInTheDocument();
  });

  test("shows the complete editable value without disclosure controls", () => {
    mockDescriptionMeasurements({ scrollHeight: 160, clientHeight: 80 });
    const currentTicket = ticket({
      description: "First editable paragraph.\n\nSecond editable paragraph.",
    });
    render(
      <TicketDetailsSection
        {...props(currentTicket, {
          editing: true,
          editForm: { ...currentTicket },
        })}
      />,
    );

    expect(screen.getByRole("textbox", { name: "Description" })).toHaveValue(
      currentTicket.description,
    );
    expect(screen.queryByRole("button", { name: "Read More" })).not.toBeInTheDocument();
  });

  test("preserves authored paragraphs as escaped plain text", () => {
    const description = "First paragraph.\n\nSecond paragraph with <script>text</script>.";
    render(<TicketDetailsSection {...props(ticket({ description }))} />);

    const rendered = screen.getByText(/First paragraph\./);
    expect(rendered).toHaveClass("preserve-line-breaks");
    expect(rendered).toHaveTextContent("<script>text</script>");
    expect(rendered.querySelector("script")).toBeNull();
  });

  test("returns to the collapsed state when another ticket is shown", async () => {
    const user = userEvent.setup();
    mockDescriptionMeasurements({ scrollHeight: 160, clientHeight: 80 });
    const firstTicket = ticket();
    const { rerender } = render(
      <TicketDetailsSection {...props(firstTicket)} />,
    );

    await user.click(screen.getByRole("button", { name: "Read More" }));
    expect(screen.getByText(/A sufficiently detailed ticket description/)).toHaveClass(
      "expanded",
    );

    const secondTicket = ticket({
      id: 53,
      title: "Another ticket",
      description: "Another long description ".repeat(20),
    });
    rerender(<TicketDetailsSection {...props(secondTicket)} />);

    expect(screen.getByText(/Another long description/)).toHaveClass("collapsed");
    expect(screen.getByRole("button", { name: "Read More" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});


describe("TicketDetailsSection Current Focus controls", () => {
  test.each(["ready", "in_progress"])(
    "lets an eligible %s Ticket become Current Focus",
    async (status) => {
      const user = userEvent.setup();
      const onFocus = vi.fn();
      render(
        <TicketDetailsSection
          {...props(ticket({ status }), { focusState: "available", onFocus })}
        />,
      );

      await user.click(screen.getByRole("button", { name: "Focus This" }));
      expect(onFocus).toHaveBeenCalledOnce();
    },
  );

  test.each(["blocked", "review", "done", "cancelled"])(
    "does not offer Focus for an ineligible %s Ticket",
    (status) => {
      render(
        <TicketDetailsSection
          {...props(ticket({ status }), { focusState: "ineligible" })}
        />,
      );

      expect(
        screen.queryByRole("button", { name: /Focus This|Make Available and Focus/ }),
      ).not.toBeInTheDocument();
    },
  );

  test("distinguishes intentionally unavailable work from ordinary Focus", async () => {
    const user = userEvent.setup();
    const onMakeAvailableAndFocus = vi.fn();
    render(
      <TicketDetailsSection
        {...props(ticket({ status: "ready" }), {
          focusState: "unavailable",
          onMakeAvailableAndFocus,
        })}
      />,
    );

    expect(screen.queryByRole("button", { name: "Focus This" })).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Make Available and Focus" }),
    );
    expect(onMakeAvailableAndFocus).toHaveBeenCalledOnce();
  });

  test("identifies Current Focus and offers immediate Undo after success", async () => {
    const user = userEvent.setup();
    const onUndoFocus = vi.fn();
    render(
      <TicketDetailsSection
        {...props(ticket(), {
          focusState: "current",
          focusNotice: "Current Focus updated.",
          canUndoFocus: true,
          onUndoFocus,
        })}
      />,
    );

    expect(screen.getByText("Current Focus")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Focus This" })).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Current Focus updated.");
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(onUndoFocus).toHaveBeenCalledOnce();
  });

  test("keeps safe focus errors inside the open Ticket Details surface", () => {
    render(
      <TicketDetailsSection
        {...props(ticket(), {
          focusState: "available",
          focusError: "Only Ready or In Progress Tickets can become Current Focus.",
        })}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Only Ready or In Progress Tickets can become Current Focus.",
    );
  });
});

