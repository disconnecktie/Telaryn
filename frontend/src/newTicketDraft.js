// Keep manual New Ticket drafts per tab and workspace; never submit recovered data.
const ttl = 24 * 60 * 60 * 1000;
function key(user) {
  return user?.id != null && user?.workspace_id != null
    ? `atlas-new-ticket:${user.id}:${user.workspace_id}` : null;
}
export function clearNewTicketDraft(user) {
  try { const name = key(user); if (name) window.sessionStorage.removeItem(name); } catch { /* Optional storage. */ }
}
export function saveNewTicketDraft(user, draft) {
  try {
    const name = key(user);
    if (!name) return;
    window.sessionStorage.setItem(name, JSON.stringify({ savedAt: Date.now(),
      form: draft.form, criteria: draft.criteria, subtasks: draft.subtasks,
      criterionInput: draft.criterionInput, subtaskInput: draft.subtaskInput,
    }));
  } catch { /* Storage restrictions must not prevent manual creation. */ }
}
export function readNewTicketDraft(user) {
  try {
    const name = key(user);
    if (!name) return null;
    const value = JSON.parse(window.sessionStorage.getItem(name));
    if (!value) return null;
    if (!Number.isFinite(value.savedAt) || Date.now() - value.savedAt > ttl ||
        typeof value.form?.title !== "string" || typeof value.form?.description !== "string" ||
        !Array.isArray(value.criteria) || !value.criteria.every(item => typeof item === "string") ||
        !Array.isArray(value.subtasks) || !value.subtasks.every(item => typeof item?.title === "string")) {
      clearNewTicketDraft(user);
      return null;
    }
    return value;
  } catch { return null; }
}
