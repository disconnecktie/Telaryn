// Owns deterministic, explainable project summary ranking outside React presentation.
const TERMINAL_TICKET_STATUSES = new Set(["done", "cancelled"]);

function normalizeProjectId(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function targetWeight(targetDate, now) {
  if (!targetDate) return { score: 0, label: null };
  const target = new Date(`${targetDate}T12:00:00`);
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.ceil((target - today) / 86400000);
  if (days < 0) return { score: 1100, label: "Past target" };
  if (days <= 7) return { score: 850, label: "Due soon" };
  if (days <= 30) return { score: 350, label: "Target approaching" };
  return { score: 0, label: null };
}

function activityTimestamp(project, projectTickets) {
  const values = [
    project.updated_at,
    ...projectTickets.map((ticket) => ticket.updated_at),
  ]
    .filter(Boolean)
    .map((value) => new Date(value).getTime())
    .filter(Number.isFinite);
  return values.length ? Math.max(...values) : 0;
}

export function rankProjectSummaries({
  projects,
  tickets,
  preferredProjectId,
  currentFocusProjectId,
  now = new Date(),
}) {
  const preferredId = normalizeProjectId(preferredProjectId);
  const focusId = normalizeProjectId(currentFocusProjectId);

  return projects
    .map((project) => {
      const projectTickets = tickets.filter(
        (ticket) => ticket.project_id === project.id,
      );
      const completed = projectTickets.filter(
        (ticket) => ticket.status === "done",
      ).length;
      const active = projectTickets.filter(
        (ticket) => !TERMINAL_TICKET_STATUSES.has(ticket.status),
      ).length;
      const inProgress = projectTickets.filter(
        (ticket) => ticket.status === "in_progress",
      ).length;
      const target = targetWeight(project.target_date, now);
      const lastActivity = activityTimestamp(project, projectTickets);
      const daysSinceActivity = lastActivity
        ? Math.max(0, (now.getTime() - lastActivity) / 86400000)
        : Number.POSITIVE_INFINITY;
      const recentWeight =
        daysSinceActivity <= 7 ? 240 : daysSinceActivity <= 30 ? 100 : 0;
      const isPreferred = project.id === preferredId;
      const hasCurrentFocus = project.id === focusId;
      const score =
        (isPreferred ? 10000 : 0)
        + (hasCurrentFocus ? 8000 : 0)
        + inProgress * 500
        + target.score
        + recentWeight
        + Math.min(active, 20) * 10;

      let reason = null;
      if (isPreferred) reason = "Default project";
      else if (hasCurrentFocus) reason = "Current Focus";
      else if (target.label) reason = target.label;
      else if (inProgress) reason = `${inProgress} in progress`;
      else if (recentWeight) reason = "Active recently";

      return {
        ...project,
        ticketCount: projectTickets.length,
        completed,
        active,
        inProgress,
        lastActivity,
        score,
        reason,
      };
    })
    .sort(
      (left, right) =>
        right.score - left.score
        || right.lastActivity - left.lastActivity
        || right.active - left.active
        || left.name.localeCompare(right.name),
    );
}
