// Presents core ticket fields while App retains the edit form and persistence boundary.
import { useLayoutEffect, useRef, useState } from "react";
import { localTicketReference } from "../../ticketReference";
import useDrawerTargetFocus from "../../hooks/useDrawerTargetFocus";
function TicketDetailsSection({
  ticket,
  mobile = false,
  projects,
  projectName,
  editing,
  editForm,
  error = null,
  canEdit,
  readOnly = false,
  onStartEditing,
  onEditFieldChange,
  focusState = "ineligible",
  focusPending = false,
  focusNotice = null,
  focusError = null,
  canUndoFocus = false,
  onFocus,
  onMakeAvailableAndFocus,
  onUndoFocus,
}) {
  const [titleFocused, setTitleFocused] = useState(false);
  const [expandedDescriptionTicketId, setExpandedDescriptionTicketId] = useState(null);
  const [descriptionOverflowing, setDescriptionOverflowing] = useState(false);
  const descriptionRef = useRef(null);
  const titleFieldRef = useRef(null);
  useDrawerTargetFocus(
    editing,
    titleFieldRef,
    error && !editForm.title.trim() ? error : null,
  );
  const descriptionExpanded = expandedDescriptionTicketId === ticket.id;
  const hasDescription = Boolean(ticket.description?.trim());
  const selectedProjectId = editing ? editForm.project_id : ticket.project_id;
  const selectedProject = projects.find((project) => project.id === selectedProjectId);
  const projectBlocksAI = selectedProject?.ai_context_enabled === false;

  // Measure the rendered clamp so short descriptions do not receive a useless control.
  useLayoutEffect(() => {
    if (editing || !hasDescription || !descriptionRef.current) {
      setDescriptionOverflowing(false);
      return undefined;
    }

    const descriptionElement = descriptionRef.current;
    const measureOverflow = () => {
      setDescriptionOverflowing(
        descriptionElement.scrollHeight > descriptionElement.clientHeight + 1,
      );
    };

    measureOverflow();
    window.addEventListener("resize", measureOverflow);
    const resizeObserver =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(measureOverflow);
    resizeObserver?.observe(descriptionElement);

    return () => {
      window.removeEventListener("resize", measureOverflow);
      resizeObserver?.disconnect();
    };
  }, [editing, hasDescription, ticket.description, ticket.id]);

  const focusAction = (
    <>
          {!editing && focusState === "available" && (
            <button
              type="button"
              className="ticket-focus-button"
              disabled={focusPending}
              onClick={onFocus}
            >
              {focusPending ? "Updating Focus…" : "Focus This"}
            </button>
          )}
          {!editing && focusState === "unavailable" && (
            <button
              type="button"
              className="ticket-focus-button"
              disabled={focusPending}
              onClick={onMakeAvailableAndFocus}
            >
              {focusPending ? "Updating Focus…" : "Make Available and Focus"}
            </button>
          )}
    </>
  );

  return (
    <>
      <div className="drawer-header">
        <div>
          <div className="drawer-ticket-reference">
            <p className="eyebrow">{localTicketReference(ticket)}</p>
            {mobile && focusAction}
            {!editing && focusState === "current" && (
              <span className="current-focus-indicator">Current Focus</span>
            )}
          </div>

          {editing ? (
            <input
              ref={titleFieldRef}
              aria-invalid={Boolean(error) && !editForm.title.trim()}
              className={`drawer-title-input ${
                titleFocused ? "is-focused" : ""
              }`}
              aria-label="Ticket title"
              maxLength="200"
              title={editForm.title}
              value={editForm.title}
              onFocus={() => setTitleFocused(true)}
              onBlur={() => setTitleFocused(false)}
              onChange={(event) =>
                onEditFieldChange("title", event.target.value)
              }
            />
          ) : (
            <h2>{ticket.title}</h2>
          )}
        </div>

      </div>

      <div className="drawer-badges">
        {editing ? (
          <select
            className={`inline-badge-select priority-badge ${editForm.priority}`}
            aria-label="Priority"
            value={editForm.priority}
            onChange={(event) =>
              onEditFieldChange("priority", event.target.value)
            }
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        ) : (
          <span className={`priority-badge ${ticket.priority}`}>
            {ticket.priority}
          </span>
        )}

        <span className={`status-badge ${ticket.status}`}>
          {ticket.status.replace("_", " ")}
        </span>
        {readOnly && <span className="neutral-badge archived">Archived · Read-only</span>}

        {editing ? (
          <select
            className="inline-badge-select neutral-badge"
            aria-label="Ticket type"
            value={editForm.ticket_type}
            onChange={(event) =>
              onEditFieldChange("ticket_type", event.target.value)
            }
          >
            <option value="task">Task</option>
            <option value="problem">Problem</option>
            <option value="request">Request</option>
            <option value="research">Research</option>
            <option value="development">Development</option>
          </select>
        ) : (
          <span className="neutral-badge">{ticket.ticket_type}</span>
        )}

        <div className="ticket-drawer-actions">
          {!mobile && focusAction}
          {canEdit && (
            <button
              type="button"
              className="section-edit-button ticket-edit-button"
              onClick={onStartEditing}
              aria-label="Edit Ticket"
            >
              Edit<span className="ticket-edit-label-suffix"> Ticket</span>
            </button>
          )}
        </div>
      </div>

      {readOnly && (
        <div className="ticket-archived-notice" role="status">
          This Ticket belongs to an archived Project. Restore the Project before changing its work.
        </div>
      )}

      {(focusNotice || focusError) && (
        <div
          className={`ticket-focus-feedback ${focusError ? "error" : "success"}`}
          role={focusError ? "alert" : "status"}
        >
          <span>{focusError || focusNotice}</span>
          {!focusError && canUndoFocus && (
            <button type="button" className="text-button" onClick={onUndoFocus}>
              Undo
            </button>
          )}
        </div>
      )}

      <section className="detail-section">
        <p className="detail-label">Project</p>
        {editing ? (
          <select
            className="inline-detail-select"
            aria-label="Project"
            value={editForm.project_id ?? ""}
            onChange={(event) =>
              onEditFieldChange(
                "project_id",
                event.target.value === "" ? null : Number(event.target.value)
              )
            }
          >
            <option value="">No project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}{project.ai_context_enabled === false ? " (Private)" : ""}
              </option>
            ))}
          </select>
        ) : (
          <p>{projectName}</p>
        )}
      </section>

      {(editing || ticket.ai_context_enabled === false || projectBlocksAI) && (
        <section className="detail-section ticket-ai-context-section">
          <p className="detail-label">
            {editing ? "Ticket privacy" : "Telaryn AI context"}
          </p>
          {editing ? (
            <label className="ticket-ai-context-toggle">
              <input
                type="checkbox"
                checked={editForm.ai_context_enabled === false}
                onChange={(event) =>
                  onEditFieldChange("ai_context_enabled", !event.target.checked)
                }
              />
              <span>
                <strong>Make this Ticket Private</strong>
                {editForm.ai_context_enabled === false && (
                  <small>
                    Telaryn will not send this Ticket’s content to an AI provider.
                  </small>
                )}
              </span>
            </label>
          ) : ticket.ai_context_enabled === false ? (
            <div className="ticket-ai-context-status private">
              <strong>Private Ticket</strong>
              <span>
                Telaryn will not send this Ticket’s content to an AI provider. Its
                Project Review excludes it.
              </span>
            </div>
          ) : (
            <div className="ticket-ai-context-status blocked">
              <strong>Protected by its Private Project</strong>
              <span>
                {selectedProject.name} is Private, so Telaryn AI cannot process this
                Ticket unless that Project’s setting changes.
              </span>
            </div>
          )}
          {editing && projectBlocksAI && (
            <p className="ticket-project-ai-note">
              The selected Project is Private, so Telaryn AI remains unavailable for
              this Ticket even if the Ticket itself is not Private.
            </p>
          )}
        </section>
      )}

      <section className="detail-section">
        <p className="detail-label">Description</p>
        {editing ? (
          <textarea
            className="inline-description-input"
            aria-label="Description"
            rows="5"
            value={editForm.description}
            onChange={(event) =>
              onEditFieldChange("description", event.target.value)
            }
          />
        ) : (
          <>
            <p
              id={`ticket-${ticket.id}-description`}
              ref={descriptionRef}
              className={`detail-description preserve-line-breaks ${
                descriptionExpanded ? "expanded" : "collapsed"
              }`}
            >
              {ticket.description || "No description provided."}
            </p>
            {hasDescription && (descriptionOverflowing || descriptionExpanded) && (
              <button
                type="button"
                className="detail-description-toggle"
                aria-controls={`ticket-${ticket.id}-description`}
                aria-expanded={descriptionExpanded}
                onClick={() =>
                  setExpandedDescriptionTicketId(
                    descriptionExpanded ? null : ticket.id,
                  )
                }
              >
                {descriptionExpanded ? "Show Less" : "Read More"}
              </button>
            )}
          </>
        )}
      </section>
    </>
  );
}

export function TicketPublicReference({ ticket }) {
  const [copied, setCopied] = useState(false);

  async function copyPublicReference() {
    if (!ticket.public_id) return;
    try {
      if (window.navigator.clipboard?.writeText) {
        await window.navigator.clipboard.writeText(ticket.public_id);
      } else {
        const input = document.createElement("textarea");
        input.value = ticket.public_id;
        input.setAttribute("readonly", "");
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        const copiedReference = document.execCommand("copy");
        input.remove();
        if (!copiedReference) throw new Error("Copy unavailable");
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  if (!ticket.public_id) return null;

  return (
    <section className="detail-section ticket-public-reference">
      <p className="detail-label">Public reference</p>
      <div>
        <code title={ticket.public_id}>{ticket.public_id}</code>
        <button
          type="button"
          className="text-button"
          onClick={copyPublicReference}
          aria-label="Copy public Ticket reference"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <small>Use this immutable reference when linking to this Ticket outside its workspace.</small>
    </section>
  );
}

export default TicketDetailsSection;

