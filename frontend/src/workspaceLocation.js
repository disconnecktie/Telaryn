// Per-tab navigation only: never persist ticket content, credentials, or drafts.
const views = new Set(["dashboard", "work", "projects", "search", "reports", "settings", "about"]);
function key(user) {
  return user?.id != null && user?.workspace_id != null
    ? `atlas-location:${user.id}:${user.workspace_id}` : null;
}
export function readWorkspaceLocation(user) {
  try {
    const name = key(user);
    if (!name) return null;
    const value = JSON.parse(window.sessionStorage.getItem(name));
    if (!value || !views.has(value.view)) return null;
    return {
      view: value.view === "dashboard" ? "work" : value.view,
      ticketId: Number.isInteger(value.ticketId) ? value.ticketId : null,
      projectId: Number.isInteger(value.projectId) ? value.projectId : null,
      interruptedEdits: value.interruptedEdits === true,
    };
  } catch { return null; }
}
export function saveWorkspaceLocation(user, location) {
  try {
    const name = key(user);
    if (name) window.sessionStorage.setItem(name, JSON.stringify({
      view: location.view,
      ticketId: location.ticketId ?? null,
      projectId: location.projectId ?? null,
      interruptedEdits: location.interruptedEdits === true,
    }));
  } catch { /* Storage can be unavailable; navigation must still work. */ }
}
export function clearWorkspaceLocation(user) {
  try {
    const name = key(user);
    if (name) window.sessionStorage.removeItem(name);
  } catch { /* Signing out must not depend on storage access. */ }
}
