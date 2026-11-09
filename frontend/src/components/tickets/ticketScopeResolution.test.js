// Verifies when a drawer update must ask for an explicit ticket outcome.
import { describe, expect, it } from "vitest";
import { requiresFinalScopeResolution } from "./ticketScopeResolution";

function state(overrides = {}) {
  return {
    criteria: [],
    criteriaDraft: [],
    subtasks: [],
    subtasksDraft: [],
    ...overrides,
  };
}

describe("requiresFinalScopeResolution", () => {
  it("prompts when the final active criterion is completed", () => {
    expect(requiresFinalScopeResolution(state({
      criteria: [{ id: 1, completed: false, deferred: false }],
      criteriaDraft: [{ id: 1, completed: true, deferred: false }],
    }))).toBe(true);
  });

  it("prompts when the final active subtask is deferred", () => {
    expect(requiresFinalScopeResolution(state({
      subtasks: [{ id: 1, status: "todo" }],
      subtasksDraft: [{ id: 1, status: "deferred" }],
    }))).toBe(true);
  });

  it("does not prompt while any active scope remains", () => {
    expect(requiresFinalScopeResolution(state({
      criteria: [
        { id: 1, completed: false, deferred: false },
        { id: 2, completed: false, deferred: false },
      ],
      criteriaDraft: [
        { id: 1, completed: true, deferred: false },
        { id: 2, completed: false, deferred: false },
      ],
    }))).toBe(false);
  });

  it("does not prompt for a ticket that started without active scope", () => {
    expect(requiresFinalScopeResolution(state({
      criteria: [{ id: 1, completed: true, deferred: false }],
      criteriaDraft: [{ id: 1, completed: true, deferred: false }],
    }))).toBe(false);
  });
});
