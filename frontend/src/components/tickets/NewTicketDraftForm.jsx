// Captures human-authored draft fields and structure before creation or optional review.
import AtlasReviewProgress from "./AtlasReviewProgress";
import { parseStructureList } from "./parseStructureList";
function NewTicketDraftForm({
  projects,
  form,
  criteria,
  subtasks,
  criterionInput,
  subtaskInput,
  error,
  saving,
  reviewing,
  onFormChange,
  onCriterionInputChange,
  onSubtaskInputChange,
  onAddCriterion,
  onRemoveCriterion,
  onAddSubtask,
  onRemoveSubtask,
  onCancel,
  onCreate,
  onReview,
  onCancelReview,
}) {
  const pendingCriterionCount = parseStructureList(criterionInput).length;
  const pendingSubtaskCount = parseStructureList(subtaskInput).length;
  const selectedProject = projects.find((project) => project.id === form.project_id);

  return (
    <>
      <label className="edit-field">
        <span>Title</span>

        <input
          autoFocus
          placeholder="Give this work a short title"
          value={form.title}
          onChange={(event) =>
            onFormChange({ ...form, title: event.target.value })
          }
        />
      </label>

      <label className="edit-field">
        <span>Description</span>

        <textarea
          rows="6"
          placeholder="Describe what you need, even if it's rough..."
          value={form.description}
          onChange={(event) =>
            onFormChange({ ...form, description: event.target.value })
          }
        />
      </label>

      <div className="edit-grid">
        <label className="edit-field">
          <span>Priority</span>

          <select
            value={form.priority}
            onChange={(event) =>
              onFormChange({ ...form, priority: event.target.value })
            }
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>

        <label className="edit-field">
          <span>Type</span>

          <select
            value={form.ticket_type}
            onChange={(event) =>
              onFormChange({ ...form, ticket_type: event.target.value })
            }
          >
            <option value="task">Task</option>
            <option value="problem">Problem</option>
            <option value="request">Request</option>
            <option value="research">Research</option>
            <option value="development">Development</option>
          </select>
        </label>
      </div>

      <label className="edit-field">
        <span>Project</span>

        <select
          value={form.project_id ?? ""}
          onChange={(event) =>
            onFormChange({
              ...form,
              project_id:
                event.target.value === "" ? null : Number(event.target.value),
            })
          }
        >
          <option value="">No project</option>

          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}{project.ai_context_enabled === false ? " (Private)" : ""}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="ticket-ai-context-choice">
        <legend>Telaryn AI context</legend>
        <label>
          <input
            type="checkbox"
            checked={form.ai_context_enabled === false}
            onChange={(event) =>
              onFormChange({ ...form, ai_context_enabled: !event.target.checked })
            }
          />
          <span>
            <strong>Make this Ticket Private</strong>
            <small>
              Telaryn will not send its content to an AI provider. Project Review
              will exclude it.
            </small>
          </span>
        </label>
        {selectedProject?.ai_context_enabled === false && (
          <p className="ticket-project-ai-note">
            {selectedProject.name} is Private, so Telaryn AI cannot process this
            Ticket unless that Project’s setting changes.
          </p>
        )}
      </fieldset>

      <div className="new-ticket-structure">
        <div className="new-ticket-structure-section">
          <span className="structure-label">Acceptance criteria</span>
          <form className="criterion-form" onSubmit={onAddCriterion}>
            <textarea
              rows="3"
              placeholder="Add one criterion, or paste one per line..."
              value={criterionInput}
              onChange={(event) => onCriterionInputChange(event.target.value)}
            />
            <small className="structure-entry-help">
              Enter one item per line. Paste a list to add several at once.
            </small>
            <button type="submit" disabled={!criterionInput.trim()}>
              {pendingCriterionCount > 1
                ? `Add ${pendingCriterionCount} Acceptance Criteria`
                : "Add Acceptance Criterion"}
            </button>
          </form>

          {criteria.length > 0 && (
            <div className="draft-input-list">
              {criteria.map((criterion, index) => (
                <div className="draft-input-item" key={index}>
                  <span>{criterion}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveCriterion(index)}
                    title="Remove acceptance criterion"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="new-ticket-structure-section">
          <span className="structure-label">Subtasks</span>
          <form className="criterion-form" onSubmit={onAddSubtask}>
            <textarea
              rows="3"
              placeholder="Add one subtask, or paste one per line..."
              value={subtaskInput}
              onChange={(event) => onSubtaskInputChange(event.target.value)}
            />
            <small className="structure-entry-help">
              Enter one item per line. Paste a list to add several at once.
            </small>
            <button type="submit" disabled={!subtaskInput.trim()}>
              {pendingSubtaskCount > 1
                ? `Add ${pendingSubtaskCount} Subtasks`
                : "Add Subtask"}
            </button>
          </form>

          {subtasks.length > 0 && (
            <div className="draft-input-list">
              {subtasks.map((subtask, index) => (
                <div className="draft-input-item" key={index}>
                  <span>{subtask.title}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveSubtask(index)}
                    title="Remove subtask"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <div className="ai-review-error">{error}</div>}

      <div className="modal-actions">
        <button className="secondary-button" onClick={onCancel}>
          Cancel
        </button>

        <button
          className="secondary-button"
          onClick={onCreate}
          disabled={saving || reviewing}
        >
          {saving ? "Creating..." : "Create Ticket"}
        </button>

        {reviewing ? (
          <AtlasReviewProgress onCancel={onCancelReview} />
        ) : (
          <button
            className="ai-button"
            onClick={onReview}
            disabled={
              saving
              || form.ai_context_enabled === false
              || selectedProject?.ai_context_enabled === false
            }
            title={
              form.ai_context_enabled === false
                ? "Private Tickets are not sent to Telaryn AI."
                : selectedProject?.ai_context_enabled === false
                  ? "This Ticket's Private Project is not sent to Telaryn AI."
                  : undefined
            }
          >
            {error ? "✨ Retry Review with Telaryn" : "✨ Review with Telaryn"}
          </button>
        )}
      </div>
    </>
  );
}

export default NewTicketDraftForm;

