// Provides the focused status-transition form and its required human context.
import { useRef } from "react";
import useDrawerTargetFocus from "../../hooks/useDrawerTargetFocus";
function TicketStatusSection({
  open,
  form,
  error,
  onSelectStatus,
  onCancel,
}) {
  const statusFieldRef = useRef(null);
  useDrawerTargetFocus(open, statusFieldRef, error);

  if (!open) {
    return null;
  }

  return (
    <section className="edit-ticket-panel status-change-panel">
      <p className="eyebrow">Ticket Status</p>
      <p className="muted">
        Choose the status to include with the rest of this ticket update.
      </p>

      <label className="edit-field">
        <span>New status</span>
        <select
          ref={statusFieldRef}
          aria-label="New status"
          value={form.status}
          onChange={(event) => onSelectStatus(event.target.value)}
        >
          <option value="ready">Ready</option>
          <option value="in_progress">In Progress</option>
          <option value="blocked">Blocked</option>
          <option value="review">Review</option>
          <option value="done">Done</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </label>

      {error && <div className="ai-review-error">{error}</div>}

      <div className="edit-actions">
        <button className="secondary-button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </section>
  );
}

export default TicketStatusSection;
