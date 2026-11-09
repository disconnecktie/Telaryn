// Renders executable ticket structure while App owns its staged drawer-session state.
import { useRef } from "react";
import "./SubtasksSection.css";
import { parseStructureList } from "./parseStructureList";
import StructureReference from "./StructureReference";
import { useDrawerValidationFocus } from "../../hooks/useDrawerTargetFocus";

function SubtasksSection({
  subtasks,
  editSubtasks,
  editing,
  editingKey,
  loading,
  error,
  canEdit,
  readOnly = false,
  ticket,
  onStartEditing,
  onAddItem,
  onBeginItemEdit,
  onUpdateItem,
  onCancelItemEdit,
  onSaveItemEdit,
  onRemoveItem,
  onToggleCompleted,
  onCompleteRemaining,
  onToggleDeferred,
}) {
  const sectionRef = useRef(null);
  useDrawerValidationFocus(error, sectionRef);
  const visibleSubtasks = editing ? editSubtasks : subtasks;
  const activeSubtasks = visibleSubtasks.filter(
    (subtask) => subtask.status !== "deferred"
  );
  const deferredSubtasks = visibleSubtasks.filter(
    (subtask) => subtask.status === "deferred"
  );
  const completedCount = activeSubtasks.filter(
    (subtask) => subtask.status === "done"
  ).length;
  const remainingSubtaskCount = activeSubtasks.filter(
    (subtask) => !["done", "cancelled"].includes(subtask.status)
  ).length;

  return (
    <section className="detail-section" ref={sectionRef}>
      <div className="detail-section-header">
        <p className="detail-label">Subtasks</p>
        <div className="detail-section-actions">
          <span>
            {completedCount}/{activeSubtasks.length}
            {deferredSubtasks.length > 0 && ` · ${deferredSubtasks.length} deferred`}
          </span>
          {!readOnly && remainingSubtaskCount >= 2 && (
            <button
              type="button"
              className="section-bulk-button"
              onClick={onCompleteRemaining}
              disabled={loading || editingKey !== null}
              aria-label="Complete all remaining subtasks"
            >
              Complete Remaining
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              className="section-edit-button"
              onClick={onStartEditing}
              disabled={loading}
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {editing && (
        <div className="subtask-editor">
          {editSubtasks.map((subtask, index) =>
            editingKey === subtask.clientKey ? (
              <div
                className={`subtask-edit-row ${subtask.id ? "" : "structure-add-editor"}`}
                key={subtask.clientKey}
              >
                <StructureReference
                  ticketPublicId={ticket?.public_id}
                  prefix="ST"
                  id={subtask.id}
                  itemName="Subtask"
                />
                <label className="edit-field">
                  <span>Subtask {index + 1} title</span>
                  <textarea
                    autoFocus
                    aria-invalid={Boolean(error) && !subtask.title.trim()}
                    rows="2"
                    maxLength={subtask.id ? 200 : undefined}
                    placeholder={subtask.id ? "What needs to be done?" : "Add one subtask, or paste one per line..."}
                    value={subtask.title}
                    onChange={(event) =>
                      onUpdateItem(
                        subtask.clientKey,
                        "title",
                        event.target.value
                      )
                    }
                  />
                </label>
                {!subtask.id && (
                  <small className="structure-entry-help">
                    Enter one item per line. Paste a list to add several at once.
                  </small>
                )}
                <label className="edit-field">
                  <span>Description (optional)</span>
                  <textarea
                    rows="2"
                    placeholder="Add useful context or a completion check..."
                    value={subtask.description || ""}
                    onChange={(event) =>
                      onUpdateItem(
                        subtask.clientKey,
                        "description",
                        event.target.value
                      )
                    }
                  />
                </label>
                <div className="subtask-edit-actions">
                  <small>
                    {subtask.id
                      ? "Staged in this drawer session."
                      : "Items will be staged in this drawer session."}
                  </small>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => onCancelItemEdit(subtask.clientKey)}
                  >
                    {subtask.id ? "Undo" : "Cancel"}
                  </button>
                  <button
                    type="button"
                    className="ai-button"
                    onClick={() => onSaveItemEdit(subtask.clientKey)}
                    disabled={!subtask.title.trim()}
                  >
                    {!subtask.id && parseStructureList(subtask.title).length > 1
                      ? `Add ${parseStructureList(subtask.title).length} Subtasks`
                      : subtask.id
                        ? "Done"
                        : "Add Subtask"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="subtask-edit-summary" key={subtask.clientKey}>
                <button
                  className={`subtask-check ${subtask.status === "done" ? "complete" : ""}`}
                  onClick={() => onToggleCompleted(subtask)}
                  disabled={readOnly}
                  title={subtask.status === "done" ? "Mark incomplete" : "Mark complete"}
                >
                  {subtask.status === "done" ? "✓" : ""}
                </button>
                <StructureReference
                  ticketPublicId={ticket?.public_id}
                  prefix="ST"
                  id={subtask.id}
                  itemName="Subtask"
                />
                <div className="subtask-content">
                  <p
                    className={
                      subtask.status === "done"
                        ? "subtask-title completed"
                        : "subtask-title"
                    }
                  >
                    {subtask.title}
                  </p>
                  {subtask.description && (
                    <p className="subtask-description preserve-line-breaks">
                      {subtask.description}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  className="scope-defer-button"
                  onClick={() => onToggleDeferred(subtask)}
                  disabled={readOnly}
                  disabled={readOnly || editingKey !== null}
                >
                  {subtask.status === "deferred" ? "Restore" : "Defer"}
                </button>
                <button
                  type="button"
                  className="subtask-edit-button"
                  onClick={() => onBeginItemEdit(subtask.clientKey)}
                  disabled={readOnly || editingKey !== null}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="structure-remove-button"
                  onClick={() => onRemoveItem(subtask.clientKey)}
                  disabled={readOnly || editingKey !== null}
                >
                  Remove
                </button>
              </div>
            )
          )}

          <button
            type="button"
            className={`add-subtask-button ${editSubtasks.length === 0 ? "empty-structure-add-button" : ""}`}
            onClick={onAddItem}
            disabled={readOnly || editingKey !== null}
          >
            + Add Subtask
          </button>
        </div>
      )}

      {loading ? (
        <p className="muted">Loading subtasks...</p>
      ) : editing ? null : subtasks.length === 0 ? (
        <p className="muted">No subtasks yet.</p>
      ) : (
        <div className="subtask-list">
          {subtasks.filter((subtask) => subtask.status !== "deferred").map((subtask) => (
            <div className="subtask-row" key={subtask.id}>
              <button
                className={`subtask-check ${
                  subtask.status === "done" ? "complete" : ""
                }`}
                onClick={() => onToggleCompleted(subtask)}
                  disabled={readOnly}
                title={
                  subtask.status === "done" ? "Mark incomplete" : "Mark complete"
                }
              >
                {subtask.status === "done" ? "✓" : ""}
              </button>

              <StructureReference
                  ticketPublicId={ticket?.public_id}
                prefix="ST"
                id={subtask.id}
                itemName="Subtask"
              />
              <div className="subtask-content">
                <p
                  className={
                    subtask.status === "done"
                      ? "subtask-title completed"
                      : "subtask-title"
                  }
                >
                  {subtask.title}
                </p>
                {subtask.description && (
                  <p className="subtask-description preserve-line-breaks">{subtask.description}</p>
                )}
              </div>
              <button
                type="button"
                className="scope-defer-button"
                onClick={() => onToggleDeferred(subtask)}
                  disabled={readOnly}
              >
                Defer
              </button>
            </div>
          ))}
        </div>
      )}

      {!editing && deferredSubtasks.length > 0 && (
        <details className="deferred-scope">
          <summary>Deferred Scope ({deferredSubtasks.length})</summary>
          <div className="subtask-list">
            {deferredSubtasks.map((subtask) => (
              <div className="subtask-row deferred" key={subtask.id}>
                <span className="scope-state-badge">Deferred</span>
                <div className="scope-item-copy">
                  <StructureReference
                  ticketPublicId={ticket?.public_id}
                    prefix="ST"
                    id={subtask.id}
                    itemName="Subtask"
                  />
                  <p className="subtask-title">{subtask.title}</p>
                  {subtask.description && <p className="subtask-description preserve-line-breaks">{subtask.description}</p>}
                  {subtask.deferred_reason && <small>{subtask.deferred_reason}</small>}
                </div>
                <button
                  type="button"
                  className="scope-defer-button"
                  onClick={() => onToggleDeferred(subtask)}
                  disabled={readOnly}
                >
                  Restore
                </button>
              </div>
            ))}
          </div>
        </details>
      )}

      {error && <p className="criterion-error" tabIndex="-1">{error}</p>}
    </section>
  );
}

export default SubtasksSection;
