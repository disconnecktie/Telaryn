// Presents the focused create/edit workflow; project persistence stays in App.
import { PROJECT_LIFE_CONTEXTS } from "../../projectLifeContexts";
function ProjectModal({
  mode,
  form,
  error,
  saving,
  starterTicketCount = 0,
  onFormChange,
  onClose,
  onSubmit,
}) {
  const editing = mode === "edit";

  return (
    <>
      <div className="modal-overlay" onClick={onClose} />

      <div className="ticket-modal project-modal">
        <div className="modal-header">
          <div>
            <p className="eyebrow">{editing ? "EDIT PROJECT" : "NEW PROJECT"}</p>
            <h2>
              {editing
                ? "Update project details"
                : "What are you working toward?"}
            </h2>
          </div>

          <button className="close-button" onClick={onClose}>
            ×
          </button>
        </div>

        <form className="project-form" onSubmit={onSubmit}>
          {!editing && starterTicketCount > 0 && (
            <p className="muted" role="status">
              After creating this Project, Telaryn will open {starterTicketCount} proposed
              {starterTicketCount === 1 ? " Ticket" : " Tickets"} for your review. Each
              Ticket is created only after you approve its draft.
            </p>
          )}
          <label className="edit-field">
            <span>Name</span>
            <input
              autoFocus
              maxLength="200"
              placeholder="Project name"
              value={form.name}
              onChange={(event) =>
                onFormChange({
                  ...form,
                  name: event.target.value,
                })
              }
            />
          </label>

          <label className="edit-field">
            <span>Description</span>
            <small>What is this project? Add any useful scope, background, or notes.</small>
            <textarea
              rows="3"
              placeholder="Describe the project..."
              value={form.description}
              onChange={(event) => onFormChange({ ...form, description: event.target.value })}
            />
          </label>

          <label className="edit-field">
            <span>Life context</span>
            <small>Controls which Activity Reports include this project by default. Telaryn never chooses this for you.</small>
            <select
              value={form.life_context}
              onChange={(event) => onFormChange({ ...form, life_context: event.target.value })}
            >
              {PROJECT_LIFE_CONTEXTS.map((context) => (
                <option key={context.value} value={context.value}>{context.label}</option>
              ))}
            </select>
          </label>

          <label className="edit-field">
            <span>Purpose</span>
            <small>What are you trying to accomplish?</small>
            <textarea
              rows="3"
              placeholder="The outcome you want..."
              value={form.purpose}
              onChange={(event) => onFormChange({ ...form, purpose: event.target.value })}
            />
          </label>

          <label className="edit-field">
            <span>Why it matters now</span>
            <small>What need, commitment, consequence, or personal value makes this worth your attention?</small>
            <textarea
              rows="3"
              placeholder="Why this deserves attention now..."
              value={form.why_it_matters}
              onChange={(event) => onFormChange({ ...form, why_it_matters: event.target.value })}
            />
          </label>

          <fieldset className="project-ai-context-choice">
            <legend>Telaryn AI context</legend>
            <label>
              <input
                type="checkbox"
                checked={form.ai_context_enabled}
                onChange={(event) =>
                  onFormChange({
                    ...form,
                    ai_context_enabled: event.target.checked,
                  })
                }
              />
              <span>
                <strong>Allow Telaryn AI for this project</strong>
                <small>
                  Turn this off to make the project Private. Telaryn will not send
                  this project’s content to an AI provider. Workspace access stays the same.
                </small>
              </span>
            </label>
          </fieldset>

          <label className="edit-field">
            <span>Target date <small>(optional)</small></span>
            <small>When are you hoping to have this accomplished?</small>
            <input
              type="date"
              value={form.target_date}
              onChange={(event) => onFormChange({ ...form, target_date: event.target.value })}
            />
          </label>

          {error && <div className="ai-review-error">{error}</div>}

          <div className="modal-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ai-button"
              disabled={saving || !form.name.trim()}
            >
              {saving
                ? "Saving..."
                : editing
                  ? "Save Changes"
                  : "Create Project"}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

export default ProjectModal;

