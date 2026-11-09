// Presents authoritative activity sources as one readable, newest-first timeline.
import { useRef, useState } from "react";
import "./TicketActivitySection.css";
import useDrawerTargetFocus from "../../hooks/useDrawerTargetFocus";

const COLLAPSIBLE_UPDATE_LENGTH = 180;

function CollapsibleUpdate({ children, className = "" }) {
  const [expanded, setExpanded] = useState(false);
  const text = String(children || "");
  const isLong = text.length > COLLAPSIBLE_UPDATE_LENGTH || text.split("\n").length > 3;

  return (
    <div className="activity-collapsible-update">
      <p className={`${className}${isLong && !expanded ? " activity-update-clamped" : ""}`.trim()}>
        {text}
      </p>
      {isLong && (
        <button
          type="button"
          className="activity-update-toggle"
          aria-expanded={expanded}
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? "Show Less" : "Show Full Update"}
        </button>
      )}
    </div>
  );
}

function titleCase(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function parseAtlasTimestamp(value) {
  // Older SQLite rows contain UTC clock time without an offset marker.
  const hasOffset = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  return new Date(hasOffset ? value : `${value}Z`);
}

function formatValue(fieldName, value, projects) {
  if (value === null || value === undefined || value === "") {
    return "None";
  }

  if (fieldName === "project_id") {
    return projects.find((project) => project.id === value)?.name || "Project unavailable";
  }

  if (["status", "priority", "ticket_type"].includes(fieldName)) {
    return titleCase(value);
  }

  return String(value);
}

function ActivityValues({ item, projects }) {
  const previous = formatValue(item.field_name, item.previous_value, projects);
  const next = formatValue(item.field_name, item.new_value, projects);

  if (item.field_name === "description") {
    return (
      <details className="activity-description-change">
        <summary>View description changes</summary>
        <div><span>Before</span><p>{previous}</p></div>
        <div><span>After</span><p>{next}</p></div>
      </details>
    );
  }

  return (
    <p className="activity-values">
      <span>{previous}</span>
      <span aria-hidden="true">→</span>
      <strong>{next}</strong>
    </p>
  );
}

function resourceLabel(value, isCriterion) {
  if (isCriterion) {
    const state = value?.deferred ? "Deferred" : value?.completed ? "Complete" : "Incomplete";
    return `${value?.text || "Untitled criterion"} · ${state}`;
  }
  return [value?.title || "Untitled subtask", titleCase(value?.status || "todo"), value?.description]
    .filter(Boolean)
    .join(" · ");
}

function collectionChanges(item) {
  const previous = item.previous_value || [];
  const next = item.new_value || [];
  const previousById = new Map(previous.filter((value) => value.id).map((value) => [value.id, value]));
  const nextById = new Map(next.filter((value) => value.id).map((value) => [value.id, value]));
  const changes = [];
  next.forEach((value) => {
    if (!value.id || !previousById.has(value.id)) changes.push({ kind: "Added", value });
    else if (JSON.stringify(previousById.get(value.id)) !== JSON.stringify(value)) {
      changes.push({ kind: "Changed", value, previous: previousById.get(value.id) });
    }
  });
  previous.forEach((value) => {
    if (value.id && !nextById.has(value.id)) changes.push({ kind: "Removed", value });
  });
  return changes;
}

function criterionOutcome(change) {
  if (change.kind !== "Changed") return change.kind;
  if (change.previous?.deferred !== change.value?.deferred) {
    return change.value.deferred ? "Deferred" : "Restored";
  }
  if (change.previous?.completed !== change.value?.completed) {
    return change.value.completed ? "Met" : "Reopened";
  }
  return "Edited";
}

function subtaskOutcome(change) {
  if (change.kind !== "Changed") return change.kind;
  if (change.previous?.status !== change.value?.status) {
    return titleCase(change.value.status);
  }
  return "Edited";
}

function StructureChangeGroup({ title, changes, isCriterion }) {
  if (!changes.length) return null;
  return (
    <section className="activity-change-group">
      <h4>{title}<span>{changes.length}</span></h4>
      <ul>
        {changes.map((change, index) => {
          const outcome = isCriterion ? criterionOutcome(change) : subtaskOutcome(change);
          const label = isCriterion
            ? change.value?.text || "Untitled criterion"
            : change.value?.title || "Untitled subtask";
          return (
            <li key={`${title}-${change.value?.id || index}`}>
              <span className={`activity-outcome ${outcome.toLowerCase().replaceAll(" ", "-")}`}>
                {outcome}
              </span>
              <p>{label}</p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function StructureActivityValues({ item }) {
  const isCriterion = item.event_type.startsWith("acceptance_criter");
  const isCollection = ["acceptance_criteria_changed", "subtasks_changed"].includes(item.event_type);
  if (isCollection) {
    return (
      <ul className="activity-structure-changes">
        {collectionChanges(item).map((change, index) => (
          <li key={`${change.kind}-${change.value?.id || index}`}>
            <strong>{change.kind}:</strong> {resourceLabel(change.value, isCriterion)}
          </li>
        ))}
      </ul>
    );
  }
  const value = item.event_type.endsWith("_removed") ? item.previous_value : item.new_value;
  return <p className="activity-content">{resourceLabel(value, isCriterion)}</p>;
}

function DrawerSessionActivityValues({ item, projects }) {
  const previous = item.previous_value || {};
  const next = item.new_value || {};
  const ticketChanges = Object.keys(next.ticket || {}).filter(
    (field) => previous.ticket?.[field] !== next.ticket[field]
  );
  const criteriaChanges = collectionChanges({
    previous_value: previous.acceptance_criteria,
    new_value: next.acceptance_criteria,
  });
  const subtaskChanges = collectionChanges({
    previous_value: previous.subtasks,
    new_value: next.subtasks,
  });
  const changeCount = ticketChanges.length + criteriaChanges.length + subtaskChanges.length;
  const includesDescription = ticketChanges.includes("description");
  const descriptionOnly = includesDescription && changeCount === 1;
  const summary = descriptionOnly
    ? "Description changed"
    : `${changeCount} ${changeCount === 1 ? "change" : "changes"} committed`;

  return (
    <details
      className="activity-description-change"
      open={changeCount <= 3 && !includesDescription}
    >
      <summary>{summary}</summary>
      <div className="activity-change-groups">
        {ticketChanges.length > 0 && (
          <section className="activity-change-group">
            <h4>Ticket<span>{ticketChanges.length}</span></h4>
            <ul>
              {ticketChanges.map((field) => (
                <li key={field}>
                  <span className="activity-outcome edited">{titleCase(field)}</span>
                  <p>{formatValue(field, previous.ticket?.[field], projects)} → {formatValue(field, next.ticket[field], projects)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}
        <StructureChangeGroup title="Acceptance Criteria" changes={criteriaChanges} isCriterion />
        <StructureChangeGroup title="Subtasks" changes={subtaskChanges} isCriterion={false} />
      </div>
    </details>
  );
}

function AIReviewActivityValues({ item, projects }) {
  const values = item.new_value || {};
  const ticketChanges = values.ticket_changes || [];
  const criteria = values.acceptance_criteria || [];
  const subtasks = values.subtasks || [];
  const changeCount = ticketChanges.length + criteria.length + subtasks.length;
  const includesDescription = ticketChanges.some(
    (change) => change.field_name === "description"
  );

  return (
    <details
      className="activity-description-change"
      open={changeCount <= 3 && !includesDescription}
    >
      <summary>{changeCount} Telaryn {changeCount === 1 ? "suggestion" : "suggestions"} applied</summary>
      <div className="activity-change-groups">
        {ticketChanges.length > 0 && (
          <section className="activity-change-group">
            <h4>Ticket<span>{ticketChanges.length}</span></h4>
            <ul>
              {ticketChanges.map((change) => (
                <li key={change.field_name}>
                  <span className="activity-outcome edited">{titleCase(change.field_name)}</span>
                  <p>{formatValue(change.field_name, change.previous_value, projects)} → {formatValue(change.field_name, change.new_value, projects)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}
        {criteria.length > 0 && (
          <StructureChangeGroup
            title="Acceptance Criteria"
            changes={criteria.map((value) => ({ kind: "Added", value }))}
            isCriterion
          />
        )}
        {subtasks.length > 0 && (
          <StructureChangeGroup
            title="Subtasks"
            changes={subtasks.map((value) => ({ kind: "Added", value }))}
            isCriterion={false}
          />
        )}
      </div>
    </details>
  );
}

function TicketCreationActivityValues({ item }) {
  const criteria = item.new_value?.acceptance_criteria || [];
  const subtasks = item.new_value?.subtasks || [];
  const itemCount = criteria.length + subtasks.length;
  if (!itemCount) return null;

  return (
    <details className="activity-description-change" open={itemCount <= 3}>
      <summary>{itemCount} items created with ticket</summary>
      {criteria.map((criterion, index) => (
        <div key={`created-criterion-${criterion.id || index}`}>
          <span>Acceptance Criterion</span>
          <p>{resourceLabel(criterion, true)}</p>
        </div>
      ))}
      {subtasks.map((subtask, index) => (
        <div key={`created-subtask-${subtask.id || index}`}>
          <span>Subtask</span>
          <p>{resourceLabel(subtask, false)}</p>
        </div>
      ))}
    </details>
  );
}

function ProgressReviewActivityValues({ item }) {
  const result = item.new_value || {};
  return <details className="activity-description-change" open>
    <summary>{result.applied?.length || 0} progress {(result.applied?.length || 0) === 1 ? "item" : "items"} approved</summary>
    <div className="activity-change-groups">
      {result.applied?.length > 0 && <p>Completed: {result.applied.join(", ")}</p>}
      {result.stale?.length > 0 && <p>Skipped because the ticket changed: {result.stale.join(", ")}</p>}
      {result.not_selected?.length > 0 && <p>Not selected: {result.not_selected.join(", ")}</p>}
    </div>
  </details>;
}

function ActivityItem({ item, projects }) {
  const eventHeadings = {
    ticket_created: "Ticket created",
    ticket_update_added: "Update added",
    status_changed: "Status changed",
    acceptance_criterion_added: "Acceptance criterion added",
    acceptance_criterion_updated: "Acceptance criterion changed",
    acceptance_criterion_removed: "Acceptance criterion removed",
    acceptance_criteria_changed: "Acceptance criteria changed",
    subtask_added: "Subtask added",
    subtask_updated: "Subtask changed",
    subtask_removed: "Subtask removed",
    subtasks_changed: "Subtasks changed",
    drawer_session_committed: "Ticket update committed",
    ai_review_applied: "Telaryn review applied",
    ai_progress_review_applied: "Telaryn progress review applied",
  };
  let heading = eventHeadings[item.event_type] || titleCase(item.event_type);
  if (item.event_type === "ticket_field_changed") {
    heading = `${titleCase(item.field_name)} changed`;
  }
  const isStructureEvent = item.event_type.startsWith("acceptance_criter") || item.event_type.startsWith("subtask");
  const isDrawerSession = item.event_type === "drawer_session_committed";
  const isAIReview = item.event_type === "ai_review_applied";
  const isProgressReview = item.event_type === "ai_progress_review_applied";
  const actorLabel = item.actor_type === "user"
    ? item.actor_name || "Telaryn user"
    : item.actor_type === "local_user"
      ? "Legacy local activity"
      : item.actor_type === "atlas_ai"
        ? "Telaryn AI"
        : item.actor_type;

  return (
    <article className={`activity-item ${item.event_type}`}>
      <strong className="activity-heading">{heading}</strong>
      {item.content && (
        item.event_type === "ticket_update_added"
          ? <CollapsibleUpdate className="activity-content">{item.content}</CollapsibleUpdate>
          : <p className="activity-content">{item.content}</p>
      )}
      {item.event_type === "ticket_created" && item.new_value?.title && (
        <>
          <p className="activity-content">{item.new_value.title}</p>
          <TicketCreationActivityValues item={item} />
        </>
      )}
      {isStructureEvent && <StructureActivityValues item={item} />}
      {isDrawerSession && <DrawerSessionActivityValues item={item} projects={projects} />}
      {isAIReview && <AIReviewActivityValues item={item} projects={projects} />}
      {isProgressReview && <ProgressReviewActivityValues item={item} />}
      {item.field_name && item.event_type !== "ticket_created" && (
        <ActivityValues item={item} projects={projects} />
      )}
      {item.note && (
        <div className="activity-note">
          <span>Update</span>
          <CollapsibleUpdate>{item.note}</CollapsibleUpdate>
        </div>
      )}
      <div className="activity-meta">
        <span>{actorLabel}</span>
        <time dateTime={item.created_at}>
          {parseAtlasTimestamp(item.created_at).toLocaleString()}
        </time>
        {item.attachment_count > 0 && (
          <span>{item.attachment_count} {item.attachment_count === 1 ? "attachment" : "attachments"}</span>
        )}
      </div>
    </article>
  );
}

// Presents all authorized ticket history while leaving storage and loading to its hook.
function TicketActivitySection({
  items,
  projects,
  loading,
  error,
  expanded,
  adding,
  canAdd,
  draft,
  saving,
  onStartAdding,
  onDraftChange,
  onCancelAdding,
  onSave,
  onToggleExpanded,
}) {
  const visibleItems = expanded ? items : items.slice(0, 3);
  const updateFieldRef = useRef(null);
  useDrawerTargetFocus(adding, updateFieldRef);

  return (
    <section className="detail-section">
      <div className="detail-section-header">
        <p className="detail-label">Activity · {items.length}</p>
        {canAdd && (
          <button type="button" className="activity-add-button" onClick={onStartAdding}>
            + Add Update
          </button>
        )}
      </div>

      {adding && (
        <form className="activity-update-form" onSubmit={onSave}>
          <textarea
            ref={updateFieldRef}
            rows="4"
            maxLength="5000"
            placeholder="What changed, what did you learn, or what happens next?"
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
          />
          <div className="activity-attachment-boundary">
            <button type="button" disabled>Attach File</button>
            <span>Attachments are coming next. Uploading will never automatically send a file to AI.</span>
          </div>
          <div className="activity-update-actions">
            <button type="button" className="secondary-button" onClick={onCancelAdding}>Cancel</button>
            <button type="submit" className="ai-button" disabled={!draft.trim() || saving}>
              {saving ? "Saving..." : "Record Update"}
            </button>
          </div>
        </form>
      )}

      {error && <p className="criterion-error">{error}</p>}
      {loading ? (
        <p className="muted">Loading activity...</p>
      ) : items.length === 0 ? (
        <p className="muted">No progress recorded yet. Use Add Update to capture what changed, what you learned, or what happens next.</p>
      ) : (
        <>
          <div className="activity-list">
            {visibleItems.map((item) => (
              <ActivityItem
                item={item}
                projects={projects}
                key={`${item.source_type}-${item.source_id}`}
              />
            ))}
          </div>
          {items.length > 3 && (
            <button type="button" className="activity-toggle" onClick={onToggleExpanded} aria-expanded={expanded}>
              {expanded ? "Show Recent Only" : "Show History"}
            </button>
          )}
        </>
      )}
    </section>
  );
}

export default TicketActivitySection;
