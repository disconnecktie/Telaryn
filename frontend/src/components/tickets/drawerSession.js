// Produces the human-readable, reversible change set for one ticket drawer session.
const ticketFieldLabels = {
  title: "Title",
  description: "Description",
  priority: "Priority",
  ticket_type: "Ticket type",
  project_id: "Project",
  status: "Status",
};

function displayValue(field, value, projects) {
  if (field === "project_id") {
    return projects.find((project) => project.id === value)?.name || "No project";
  }
  if (value === null || value === undefined || value === "") return "None";
  return String(value).replaceAll("_", " ");
}

export function buildDrawerSessionChanges({ ticket, ticketDraft, criteria, criteriaDraft, subtasks, subtasksDraft, projects }) {
  const changes = [];
  Object.keys(ticketFieldLabels).forEach((field) => {
    const original = field === "description" ? ticket[field] || "" : ticket[field];
    const staged = field === "description" ? ticketDraft[field] || "" : ticketDraft[field];
    if (original !== staged) {
      changes.push({ key: `ticket:${field}`, kind: "updated", label: ticketFieldLabels[field], detail: `${displayValue(field, original, projects)} → ${displayValue(field, staged, projects)}` });
    }
  });

  const criteriaById = new Map(criteria.map((item) => [item.id, item]));
  const stagedCriterionIds = new Set(criteriaDraft.filter((item) => item.id).map((item) => item.id));
  criteria.filter((item) => !stagedCriterionIds.has(item.id)).forEach((item) => {
    changes.push({ key: `criterion:removed:${item.id}`, kind: "removed", label: "Remove criterion", detail: item.text });
  });
  criteriaDraft.forEach((item) => {
    const original = criteriaById.get(item.id);
    if (!original) changes.push({ key: `criterion:added:${item.clientKey}`, kind: "added", label: "Add criterion", detail: item.text });
    else if (
      original.text !== item.text.trim() ||
      original.completed !== item.completed ||
      Boolean(original.deferred) !== Boolean(item.deferred)
    ) {
      const textChanged = original.text !== item.text.trim();
      const scopeChanged = Boolean(original.deferred) !== Boolean(item.deferred);
      changes.push({
        key: `criterion:updated:${item.id}`,
        kind: "updated",
        label: scopeChanged
          ? item.deferred ? "Acceptance Criterion Deferred" : "Acceptance Criterion Restored"
          : textChanged
          ? "Acceptance Criterion Edited"
          : item.completed ? "Acceptance Criterion Met" : "Acceptance Criterion Reopened",
        detail: textChanged ? `${original.text} → ${item.text.trim()}` : item.text.trim(),
      });
    }
  });

  const subtasksById = new Map(subtasks.map((item) => [item.id, item]));
  const stagedSubtaskIds = new Set(subtasksDraft.filter((item) => item.id).map((item) => item.id));
  subtasks.filter((item) => !stagedSubtaskIds.has(item.id)).forEach((item) => {
    changes.push({ key: `subtask:removed:${item.id}`, kind: "removed", label: "Remove subtask", detail: item.title });
  });
  subtasksDraft.forEach((item) => {
    const original = subtasksById.get(item.id);
    const title = item.title.trim();
    const description = item.description?.trim() || null;
    if (!original) changes.push({ key: `subtask:added:${item.clientKey}`, kind: "added", label: "Add subtask", detail: title });
    else if (original.title !== title || (original.description || null) !== description || original.status !== item.status) {
      const contentChanged = original.title !== title || (original.description || null) !== description;
      const scopeChanged = (original.status === "deferred") !== (item.status === "deferred");
      changes.push({
        key: `subtask:updated:${item.id}`,
        kind: "updated",
        label: scopeChanged
          ? item.status === "deferred" ? "Subtask Deferred" : "Subtask Restored"
          : contentChanged
          ? "Subtask Edited"
          : item.status === "done" ? "Subtask Completed" : "Subtask Reopened",
        detail: contentChanged && original.title !== title ? `${original.title} → ${title}` : title,
      });
    }
  });
  return changes;
}
