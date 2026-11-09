// Produces staged section-level completion drafts without mutating saved scope.
export function completeRemainingCriteria(criteria) {
  return criteria.map((criterion) =>
    !criterion.completed && !criterion.deferred
      ? { ...criterion, completed: true }
      : criterion,
  );
}

export function completeRemainingSubtasks(subtasks) {
  return subtasks.map((subtask) =>
    !["done", "cancelled", "deferred"].includes(subtask.status)
      ? { ...subtask, status: "done" }
      : subtask,
  );
}
