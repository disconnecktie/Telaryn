// Protects contextual focus behavior across Ticket Drawer workflow sections.
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AcceptanceCriteriaSection from "./AcceptanceCriteriaSection";
import TicketActivitySection from "./TicketActivitySection";
import TicketDetailsSection from "./TicketDetailsSection";
import TicketStatusSection from "./TicketStatusSection";

beforeEach(() => {
  window.requestAnimationFrame = (callback) => {
    callback();
    return 1;
  };
  window.cancelAnimationFrame = vi.fn();
  window.matchMedia = vi.fn(() => ({ matches: false }));
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

function drawer(children) {
  return <div className="ticket-drawer-scroll">{children}</div>;
}

describe("Ticket Drawer contextual focus", () => {
  it("focuses Add Update only after its form opens", () => {
    const props = {
      items: [],
      projects: [],
      loading: false,
      error: null,
      expanded: false,
      adding: false,
      canAdd: true,
      draft: "",
      saving: false,
      onStartAdding: vi.fn(),
      onDraftChange: vi.fn(),
      onCancelAdding: vi.fn(),
      onSave: vi.fn(),
      onToggleExpanded: vi.fn(),
    };
    const { rerender } = render(drawer(<TicketActivitySection {...props} />));

    expect(document.activeElement).toBe(document.body);
    rerender(drawer(<TicketActivitySection {...props} adding />));

    expect(screen.getByPlaceholderText(/What changed/)).toHaveFocus();
  });

  it("focuses the title when Edit Ticket opens", () => {
    const currentTicket = {
      id: 17,
      title: "Manage ticket drawer scrolling and focus",
      description: "",
      priority: "medium",
      status: "in_progress",
      ticket_type: "task",
      project_id: 1,
    };
    const props = {
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
    };
    const { rerender } = render(drawer(<TicketDetailsSection {...props} />));

    rerender(drawer(<TicketDetailsSection {...props} editing />));

    expect(screen.getByRole("textbox", { name: "Ticket title" })).toHaveFocus();
  });

  it("focuses the status selector when Change Status opens", () => {
    const props = {
      open: false,
      form: { status: "in_progress", status_note: "" },
      error: null,
      onSelectStatus: vi.fn(),
      onCancel: vi.fn(),
    };
    const { rerender } = render(drawer(<TicketStatusSection {...props} />));

    rerender(drawer(<TicketStatusSection {...props} open />));

    expect(screen.getByRole("combobox", { name: "New status" })).toHaveFocus();
  });

  it("targets the first invalid criterion when validation fails", () => {
    const criteria = [
      { id: 1, clientKey: "one", text: "", completed: false, deferred: false },
      { id: 2, clientKey: "two", text: "", completed: false, deferred: false },
    ];
    const props = {
      ticket: { public_id: "TKT-TEST" },
      criteria,
      editCriteria: criteria,
      editing: true,
      editingKey: "one",
      loading: false,
      error: null,
      canEdit: false,
      newCriterionText: "",
      onStartEditing: vi.fn(),
      onNewCriterionTextChange: vi.fn(),
      onAddCriterion: vi.fn(),
      onBeginItemEdit: vi.fn(),
      onUpdateItem: vi.fn(),
      onCancelItemEdit: vi.fn(),
      onSaveItemEdit: vi.fn(),
      onRemoveItem: vi.fn(),
      onToggleCompleted: vi.fn(),
      onCompleteRemaining: vi.fn(),
      onToggleDeferred: vi.fn(),
    };
    const { rerender } = render(drawer(<AcceptanceCriteriaSection {...props} />));

    rerender(drawer(
      <AcceptanceCriteriaSection
        {...props}
        error="Every acceptance criterion needs text."
      />,
    ));

    expect(screen.getByRole("textbox", { name: "Acceptance criterion" })).toHaveFocus();
  });
});

