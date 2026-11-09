// Makes a staged drawer edit explicit before any API mutation is requested.
import "./DrawerStagedChangesDialog.css";
function DrawerStagedChangesDialog({
  changes,
  saving,
  note,
  noteRequired,
  hasDraftUpdate,
  resolutionRequired,
  resolutionChoice,
  currentStatusLabel,
  onResolutionChoice,
  onNoteChange,
  onConfirm,
  onKeepEditing,
  onUndoAll,
  onUndoChange,
}) {
  const hasChanges = changes.length > 0;
  const resolutionPending = resolutionRequired && !resolutionChoice;
  function closeReviewOnPointerDown(event) {
    event.preventDefault();
    document.activeElement?.blur?.();
    onKeepEditing();
  }
  const resolutionHelp = {
    review: "The work is ready to be checked before closing.",
    done: "The ticket and its planned work will be completed.",
    cancelled: "The ticket will be cancelled. Completed work is preserved; explain the cancellation below.",
    keep: "Telaryn will record the scope changes without changing the ticket status.",
  };
  const updateNoteField = (
    <label className="drawer-session-note">
      {hasDraftUpdate && <small>A drafted Ticket Update will be recorded with this commit.</small>}
      <span>Update Note{noteRequired ? " (required)" : " (optional)"}</span>
      <textarea rows="3" maxLength="2000" value={note} onChange={(event) => onNoteChange(event.target.value)} placeholder="Briefly explain what changed, why, or what happens next..." />
      {noteRequired && !note.trim() && <small>Context is required for this update.</small>}
    </label>
  );

  return (
    <div className="drawer-staging-backdrop" role="presentation">
      <section className="drawer-staging-dialog" role="dialog" aria-modal="true" aria-labelledby="staged-changes-title">
        <header className="drawer-staging-header">
          <button
            type="button"
            className="close-button drawer-staging-close"
            onPointerDown={closeReviewOnPointerDown}
            onClick={onKeepEditing}
            disabled={saving}
            title="Keep working"
            aria-label="Close ticket update review"
          >
            ×
          </button>
          <p className="eyebrow">Ticket Update</p>
          <h2 id="staged-changes-title">Review Ticket Update</h2>
          <p className="muted">Confirm the outcomes Telaryn will record together in one update.</p>
        </header>

        <div className={`drawer-staging-content${resolutionRequired ? " has-resolution" : ""}`}>
        {resolutionRequired && (
          <div className="drawer-staging-pinned">
            <section className="scope-resolution" aria-labelledby="scope-resolution-title">
            <p id="scope-resolution-title" className="scope-resolution-title">
              All active planned work has been resolved
            </p>
            <label className="scope-resolution-field">
              <span>Ticket outcome</span>
              <select
                aria-label="Ticket outcome"
                value={resolutionChoice || ""}
                onChange={(event) => onResolutionChoice(event.target.value)}
              >
                <option value="" disabled>Choose an outcome...</option>
                <option value="review">Move to Review</option>
                <option value="done">Mark Done</option>
                <option value="cancelled">Mark Cancelled</option>
                <option value="keep">Keep {currentStatusLabel}</option>
              </select>
            </label>
            <p className="scope-resolution-help">
              {resolutionChoice
                ? resolutionHelp[resolutionChoice]
                : "Choose what Telaryn should do with the ticket when this update is committed."}
            </p>
            {resolutionPending && (
              <small className="scope-resolution-required">
                Select a ticket outcome to continue.
              </small>
            )}
            </section>
            {updateNoteField}
          </div>
        )}

        <div className="drawer-staging-changes">
          {hasChanges ? <ul className="staged-change-list">{changes.map((change) => (
            <li key={change.key} className={`staged-change ${change.kind}`}>
              <strong>{change.label}</strong>
              <span>{change.detail}</span>
              <button type="button" className="staged-change-undo" onClick={() => onUndoChange(change.key)} disabled={saving}>Undo Change</button>
            </li>
          ))}</ul> : <p className="muted">There are no changes to commit.</p>}
          {!resolutionRequired && updateNoteField}
        </div>
        </div>
        <div className="drawer-staging-actions">
          <button type="button" className="secondary-button" onClick={onUndoAll} disabled={saving}>Undo All Changes</button>
          <div><button type="button" className="secondary-button" onClick={onKeepEditing} disabled={saving}>Keep Working</button><button type="button" className="ai-button" onClick={onConfirm} disabled={!hasChanges || saving || resolutionPending || (noteRequired && !note.trim())}>{saving ? "Committing..." : "Commit Changes"}</button></div>
        </div>
      </section>
    </div>
  );
}
export default DrawerStagedChangesDialog;
