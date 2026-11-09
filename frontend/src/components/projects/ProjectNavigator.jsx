// Owns bounded active and archived Project discovery without mixing lifecycle states.
import { useEffect, useMemo, useState } from "react";

import { localProjectReference } from "../../projectReference";
import {
  ARCHIVE_REASONS,
  projectArchiveReasonLabel,
  projectArchiveReasonValue,
} from "../../projectArchiveReasons";
import { rankProjectSummaries } from "./projectRanking";
import { PROJECT_LIFE_CONTEXTS, projectLifeContextLabel } from "../../projectLifeContexts";

function ProjectNavigatorItem({ summary, selected, archived = false, onSelect }) {
  return (
    <button
      type="button"
      className={`project-navigator-item ${selected ? "selected" : ""} ${archived ? "archived" : ""}`}
      aria-pressed={selected}
      onClick={onSelect}
    >
      <span className="project-navigator-item-topline">
        <strong>{localProjectReference(summary)} · {summary.name}</strong>
        <span className="project-navigator-item-labels">
          {archived && (
            <em className="project-archived-badge">
              {projectArchiveReasonLabel(summary.archive_reason)}
            </em>
          )}
          {summary.ai_context_enabled === false && <em className="project-private-badge">Private</em>}
          <em className="project-life-context-badge">{projectLifeContextLabel(summary.life_context)}</em>
          {!archived && summary.reason && (
            <em className={summary.reason === "Default project" ? "project-default-badge" : undefined}>
              {summary.reason}
            </em>
          )}
        </span>
      </span>
      <span className="project-navigator-item-meta">
        {summary.ticketCount} {summary.ticketCount === 1 ? "ticket" : "tickets"}
        <span aria-hidden="true">•</span>
        {summary.completed}/{summary.ticketCount} complete
      </span>
      {!archived && summary.target_date && (
        <span className="project-navigator-target">Target {summary.target_date}</span>
      )}
    </button>
  );
}

function ProjectNavigator({
  projects,
  archivedProjects = [],
  tickets,
  archivedTickets = [],
  selectedProjectId,
  preferredProjectId,
  currentFocusProjectId,
  unassignedTickets,
  onSelectProject,
  onCreateProject,
}) {
  const selectedIsArchived = archivedProjects.some(
    (project) => project.id === selectedProjectId
  );
  const selectedIsActive = selectedProjectId === "unassigned"
    ? unassignedTickets.length > 0
    : projects.some((project) => project.id === selectedProjectId);
  const [requestedCollection, setRequestedCollection] = useState(
    selectedIsArchived ? "archived" : "active"
  );
  const collection = selectedIsArchived
    ? "archived"
    : selectedIsActive
      ? "active"
      : requestedCollection;
  const [filter, setFilter] = useState("");
  const [lifeContextFilter, setLifeContextFilter] = useState("all");
  const [visibleArchiveReasons, setVisibleArchiveReasons] = useState(
    () => new Set(ARCHIVE_REASONS.map((reason) => reason.value)),
  );

  useEffect(() => {
    if (
      selectedProjectId != null
      && !selectedIsArchived
      && !selectedIsActive
    ) {
      onSelectProject(null);
    }
  }, [
    onSelectProject,
    selectedIsActive,
    selectedIsArchived,
    selectedProjectId,
  ]);

  function selectCollection(nextCollection) {
    if (nextCollection === collection) return;
    setRequestedCollection(nextCollection);
    setFilter("");
    onSelectProject(null);
  }

  const activeSummaries = useMemo(
    () => rankProjectSummaries({
      projects,
      tickets,
      preferredProjectId,
      currentFocusProjectId,
    }),
    [currentFocusProjectId, preferredProjectId, projects, tickets],
  );
  const archivedSummaries = useMemo(
    () => rankProjectSummaries({
      projects: archivedProjects,
      tickets: archivedTickets,
      preferredProjectId: null,
      currentFocusProjectId: null,
    }),
    [archivedProjects, archivedTickets],
  );
  const summaries = collection === "archived" ? archivedSummaries : activeSummaries;
  const normalizedFilter = filter.trim().toLocaleLowerCase();
  const filteredSummaries = summaries.filter((project) =>
    project.name.toLocaleLowerCase().includes(normalizedFilter)
    && (lifeContextFilter === "all" || project.life_context === lifeContextFilter)
    && (
      collection !== "archived"
      || visibleArchiveReasons.has(projectArchiveReasonValue(project))
    ),
  );

  function toggleArchiveReason(reason) {
    setVisibleArchiveReasons((current) => {
      const next = new Set(current);
      if (next.has(reason)) next.delete(reason);
      else next.add(reason);
      return next;
    });
  }
  const showUnassigned = collection === "active" && unassignedTickets.length > 0
    && "unassigned".includes(normalizedFilter);

  return (
    <aside className="project-navigator-shell" aria-label="Project Navigator">
      <div className="project-navigator-body">
        <div className="project-navigator-heading">
          <div>
            <p className="eyebrow">YOUR PROJECTS</p>
            <h2>Project Navigator</h2>
          </div>
          <span>
            {collection === "archived"
              ? archivedProjects.length
              : projects.length + (unassignedTickets.length ? 1 : 0)}
          </span>
        </div>

        <div className="project-collection-switcher" aria-label="Project lifecycle">
          <button
            type="button"
            aria-pressed={collection === "active"}
            onClick={() => selectCollection("active")}
          >
            Active
          </button>
          <button
            type="button"
            aria-pressed={collection === "archived"}
            onClick={() => selectCollection("archived")}
          >
            Archived <span>{archivedProjects.length}</span>
          </button>
        </div>

        <label className="project-navigator-filter">
          <span>Filter projects</span>
          <input
            type="search"
            value={filter}
            placeholder={collection === "archived" ? "Find archived work" : "Find a project"}
            onChange={(event) => setFilter(event.target.value)}
          />
        </label>

        <label className="project-navigator-filter">
          <span>Life context</span>
          <select value={lifeContextFilter} onChange={(event) => setLifeContextFilter(event.target.value)}>
            <option value="all">All contexts</option>
            {PROJECT_LIFE_CONTEXTS.map((context) => (
              <option key={context.value} value={context.value}>{context.label}</option>
            ))}
          </select>
        </label>

        {collection === "archived" && (
          <details className="project-archive-filter-menu">
            <summary>
              <span>Show archive reasons</span>
              <strong>
                {visibleArchiveReasons.size === ARCHIVE_REASONS.length
                  ? "All"
                  : `${visibleArchiveReasons.size} of ${ARCHIVE_REASONS.length}`}
              </strong>
            </summary>
            <div role="group" aria-label="Visible archive reasons">
              {ARCHIVE_REASONS.map((reason) => (
                <label key={reason.value}>
                  <input
                    type="checkbox"
                    checked={visibleArchiveReasons.has(reason.value)}
                    onChange={() => toggleArchiveReason(reason.value)}
                  />
                  <span>{reason.label}</span>
                </label>
              ))}
            </div>
          </details>
        )}

        <div className="project-navigator-list">
          {filteredSummaries.map((project) => (
            <ProjectNavigatorItem
              key={project.id}
              summary={project}
              archived={collection === "archived"}
              selected={selectedProjectId === project.id}
              onSelect={() => onSelectProject(project.id)}
            />
          ))}

          {showUnassigned && (
            <ProjectNavigatorItem
              summary={{
                name: "Unassigned",
                ticketCount: unassignedTickets.length,
                completed: unassignedTickets.filter((ticket) => ticket.status === "done").length,
                target_date: null,
                reason: null,
              }}
              selected={selectedProjectId === "unassigned"}
              onSelect={() => onSelectProject("unassigned")}
            />
          )}

          {!filteredSummaries.length && !showUnassigned && (
            <p className="project-navigator-empty">
              {filter.trim()
                ? `No ${collection} project names match “${filter.trim()}”.`
                : collection === "archived" && archivedProjects.length > 0
                  ? "No archived Projects match the selected reasons."
                  : collection === "archived"
                    ? "No Projects have been archived."
                    : "No active Projects yet."}
            </p>
          )}
        </div>

        {collection === "active" && (
          <button
            type="button"
            className="secondary-button project-navigator-create"
            onClick={onCreateProject}
          >
            + New Project
          </button>
        )}
      </div>
    </aside>
  );
}

export default ProjectNavigator;
