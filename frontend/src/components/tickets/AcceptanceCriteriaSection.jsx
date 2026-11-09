// Renders ticket acceptance criteria and its isolated edit interaction.
import { useRef } from "react";
import { parseStructureList } from "./parseStructureList";
import StructureReference from "./StructureReference";
import { useDrawerValidationFocus } from "../../hooks/useDrawerTargetFocus";

function AcceptanceCriteriaSection({
  criteria,
  editCriteria,
  editing,
  editingKey,
  loading,
  error,
  canEdit,
  readOnly = false,
  ticket,
  newCriterionText,
  onStartEditing,
  onNewCriterionTextChange,
  onAddCriterion,
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
  const visibleCriteria = editing ? editCriteria : criteria;
  const activeCriteria = visibleCriteria.filter((criterion) => !criterion.deferred);
  const deferredCriteria = visibleCriteria.filter((criterion) => criterion.deferred);
  const displayedCriteria = editing ? visibleCriteria : activeCriteria;
  const completedCount = activeCriteria.filter(
    (criterion) => criterion.completed
  ).length;
  const remainingCriteriaCount = activeCriteria.length - completedCount;
  const pendingCriterionCount = parseStructureList(newCriterionText).length;

  return (
    <section className="detail-section" ref={sectionRef}>
      <div className="detail-section-header">
        <p className="detail-label">Acceptance criteria</p>
        <div className="detail-section-actions">
          <span>
            {completedCount}/{activeCriteria.length}
            {deferredCriteria.length > 0 && ` · ${deferredCriteria.length} deferred`}
          </span>
          {!readOnly && remainingCriteriaCount >= 2 && (
            <button
              type="button"
              className="section-bulk-button"
              onClick={onCompleteRemaining}
              disabled={loading || editingKey !== null}
              aria-label="Complete all remaining acceptance criteria"
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

      {editing && editingKey === "new-criterion" && (
        <form
          className="structure-item-editor structure-add-editor"
          onSubmit={onAddCriterion}
        >
          <textarea
            className="criterion-edit-input"
            aria-label="New acceptance criterion"
            aria-invalid={Boolean(error) && !newCriterionText.trim()}
            rows="3"
            placeholder="Add one criterion, or paste one per line..."
            value={newCriterionText}
            onChange={(event) =>
              onNewCriterionTextChange(event.target.value)
            }
            autoFocus
          />
          <small className="structure-entry-help">
            Enter one item per line. Paste a list to add several at once.
          </small>
          <div className="subtask-edit-actions">
            <small>Items will be staged in this drawer session.</small>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onCancelItemEdit("new-criterion")}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ai-button"
              disabled={!newCriterionText.trim()}
            >
              {pendingCriterionCount > 1
                ? `Add ${pendingCriterionCount} Acceptance Criteria`
                : "Add Acceptance Criterion"}
            </button>
          </div>
        </form>
      )}

      {error && <p className="criterion-error" tabIndex="-1">{error}</p>}

      {loading ? (
        <p className="muted">Loading acceptance criteria...</p>
      ) : visibleCriteria.length === 0 ? (
        <p className="muted">No acceptance criteria yet.</p>
      ) : (
        <div className="criterion-list">
          {displayedCriteria.map((criterion) => (
            <div
              className={`criterion-row ${editing ? "editing" : ""} ${criterion.deferred ? "deferred" : ""}`}
              key={criterion.clientKey || criterion.id}
            >
              {editing ? (
                editingKey === criterion.clientKey ? (
                  <div className="structure-item-editor">
                    <StructureReference
                      ticketPublicId={ticket?.public_id}
                      prefix="AC"
                      id={criterion.id}
                      itemName="Acceptance criterion"
                    />
                    <input
                      className="criterion-edit-input"
                      aria-label="Acceptance criterion"
                      aria-invalid={Boolean(error) && !criterion.text.trim()}
                      value={criterion.text}
                      onChange={(event) =>
                        onUpdateItem(criterion.clientKey, event.target.value)
                      }
                    />
                    <div className="subtask-edit-actions">
                      <small>Staged in this drawer session.</small>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => onCancelItemEdit(criterion.clientKey)}
                      >
                        Undo
                      </button>
                      <button
                        type="button"
                        className="ai-button"
                        onClick={() => onSaveItemEdit(criterion.clientKey)}
                        disabled={!criterion.text.trim()}
                      >
                        Done
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="subtask-edit-summary">
                    <button
                      className={`subtask-check ${criterion.completed ? "complete" : ""}`}
                      onClick={() => onToggleCompleted(criterion)}
                    disabled={readOnly}
                      title={criterion.completed ? "Mark incomplete" : "Mark complete"}
                    >
                      {criterion.completed ? "✓" : ""}
                    </button>
                    <StructureReference
                      ticketPublicId={ticket?.public_id}
                      prefix="AC"
                      id={criterion.id}
                      itemName="Acceptance criterion"
                    />
                    <p
                      className={
                        criterion.completed
                          ? "criterion-text completed"
                          : "criterion-text"
                      }
                    >
                      {criterion.text}
                    </p>
                    <button
                      type="button"
                      className="scope-defer-button"
                      onClick={() => onToggleDeferred(criterion)}
                      disabled={readOnly}
                      disabled={readOnly || editingKey !== null}
                    >
                      {criterion.deferred ? "Restore" : "Defer"}
                    </button>
                    <button
                      type="button"
                      className="subtask-edit-button"
                      onClick={() => onBeginItemEdit(criterion.clientKey)}
                      disabled={readOnly || editingKey !== null}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="structure-remove-button"
                      onClick={() => onRemoveItem(criterion.clientKey)}
                      disabled={readOnly || editingKey !== null}
                    >
                      Remove
                    </button>
                  </div>
                )
              ) : (
                <>
                  <button
                    className={`subtask-check ${
                      criterion.completed ? "complete" : ""
                    }`}
                    onClick={() => onToggleCompleted(criterion)}
                    disabled={readOnly}
                    title={
                      criterion.completed ? "Mark incomplete" : "Mark complete"
                    }
                  >
                    {criterion.completed ? "✓" : ""}
                  </button>
                  <StructureReference
                      ticketPublicId={ticket?.public_id}
                    prefix="AC"
                    id={criterion.id}
                    itemName="Acceptance criterion"
                  />
                  <p
                    className={
                      criterion.completed
                        ? "criterion-text completed"
                        : "criterion-text"
                    }
                  >
                    {criterion.text}
                  </p>
                  <button
                    type="button"
                    className="scope-defer-button"
                    onClick={() => onToggleDeferred(criterion)}
                      disabled={readOnly}
                  >
                    Defer
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {!editing && deferredCriteria.length > 0 && (
        <details className="deferred-scope">
          <summary>Deferred Scope ({deferredCriteria.length})</summary>
          <div className="criterion-list">
            {deferredCriteria.map((criterion) => (
              <div className="criterion-row deferred" key={criterion.id}>
                <span className="scope-state-badge">Deferred</span>
                <div className="scope-item-copy">
                  <StructureReference
                      ticketPublicId={ticket?.public_id}
                    prefix="AC"
                    id={criterion.id}
                    itemName="Acceptance criterion"
                  />
                  <p className="criterion-text">{criterion.text}</p>
                  {criterion.deferred_reason && <small>{criterion.deferred_reason}</small>}
                </div>
                <button
                  type="button"
                  className="scope-defer-button"
                  onClick={() => onToggleDeferred(criterion)}
                      disabled={readOnly}
                >
                  Restore
                </button>
              </div>
            ))}
          </div>
        </details>
      )}

      {editing && editingKey !== "new-criterion" && (
        <button
          type="button"
          className={`add-subtask-button ${visibleCriteria.length === 0 ? "empty-structure-add-button" : ""}`}
          onClick={() => onBeginItemEdit("new-criterion")}
          disabled={readOnly || editingKey !== null}
        >
          + Add Acceptance Criterion
        </button>
      )}

    </section>
  );
}

export default AcceptanceCriteriaSection;
