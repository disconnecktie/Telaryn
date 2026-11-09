// Verifies bulk completion changes only active incomplete items in one section.
import { describe, expect, it } from "vitest";
import {
  completeRemainingCriteria,
  completeRemainingSubtasks,
} from "./bulkScopeCompletion";

describe("bulk scope completion", () => {
  it("completes active criteria while preserving completed and deferred criteria", () => {
    const criteria = [
      { id: 1, completed: false, deferred: false },
      { id: 2, completed: true, deferred: false },
      { id: 3, completed: false, deferred: true },
    ];

    const completed = completeRemainingCriteria(criteria);

    expect(completed.map((item) => item.completed)).toEqual([true, true, false]);
    expect(completed[1]).toBe(criteria[1]);
    expect(completed[2]).toBe(criteria[2]);
    expect(criteria[0].completed).toBe(false);
  });

  it("completes active subtasks while preserving terminal and deferred subtasks", () => {
    const subtasks = [
      { id: 1, status: "todo" },
      { id: 2, status: "in_progress" },
      { id: 3, status: "done" },
      { id: 4, status: "cancelled" },
      { id: 5, status: "deferred" },
    ];

    const completed = completeRemainingSubtasks(subtasks);

    expect(completed.map((item) => item.status)).toEqual([
      "done",
      "done",
      "done",
      "cancelled",
      "deferred",
    ]);
    expect(completed[2]).toBe(subtasks[2]);
    expect(completed[3]).toBe(subtasks[3]);
    expect(completed[4]).toBe(subtasks[4]);
  });

  it("keeps criteria and subtask operations independent", () => {
    const criteria = [{ id: 1, completed: false, deferred: false }];
    const subtasks = [{ id: 1, status: "todo" }];

    completeRemainingCriteria(criteria);

    expect(subtasks[0].status).toBe("todo");
    expect(criteria[0].completed).toBe(false);
  });
});
