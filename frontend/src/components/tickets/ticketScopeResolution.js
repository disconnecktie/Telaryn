// Keeps final-scope workflow rules independent from drawer presentation.
const INACTIVE_SUBTASK_STATUSES = new Set(["done", "cancelled", "deferred"]);

export function isCriterionActive(criterion) {
  return !criterion.completed && !criterion.deferred;
}

export function isSubtaskActive(subtask) {
  return !INACTIVE_SUBTASK_STATUSES.has(subtask.status);
}

// Prompt only when this update clears work that was active when the drawer opened.
// Tickets that already had no planned work should not be nagged on unrelated edits.
export function requiresFinalScopeResolution({
  criteria,
  criteriaDraft,
  subtasks,
  subtasksDraft,
}) {
  const activeBefore =
    criteria.filter(isCriterionActive).length +
    subtasks.filter(isSubtaskActive).length;
  const activeAfter =
    criteriaDraft.filter(isCriterionActive).length +
    subtasksDraft.filter(isSubtaskActive).length;

  return activeBefore > 0 && activeAfter === 0;
}
