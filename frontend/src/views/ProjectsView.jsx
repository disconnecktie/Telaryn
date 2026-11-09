// Lets users browse active and archived Project work without duplicating ticket state ownership.
import { useRef, useState } from "react";
import { localTicketReference } from "../ticketReference";
import { localProjectReference } from "../projectReference";
import ProjectContextPanel, { ProjectPublicReference } from "../components/projects/ProjectContextPanel";
import ProjectExportButton from "../components/projects/ProjectExportButton";
import ProjectLifecycle from "../components/projects/ProjectLifecycle";
import ProjectNavigator from "../components/projects/ProjectNavigator";
import ProjectReviewPanel from "../components/projects/ProjectReviewPanel";
import ProjectWorkOverview, { ProjectHistory } from "../components/projects/ProjectWorkOverview";
import { formatLocalDateTime } from "../time";
import { ARCHIVE_REASONS, projectArchiveReasonLabel } from "../projectArchiveReasons";
import { pinCurrentFocusTicket } from "./focusTicketOrdering";
import "./ProjectsView.css";

const TERMINAL_TICKET_STATUSES = new Set(["done", "cancelled"]);

function ProjectsView({
  projects,
  archivedProjects = [],
  tickets,
  archivedTickets = [],
  selectedProjectId,
  preferredProjectId,
  onDefaultProjectChange,
  savingDefaultProject,
  defaultProjectError,
  currentFocusProjectId,
  currentFocusTicketId,
  onSelectProject,
  onCreateProject,
  onEditProject,
  onArchiveProject,
  onClassifyArchivedProject,
  onRestoreProject,
  projectArchivePending = false,
  projectArchiveError = null,
  onOpenTicket,
}) {
  const [ticketVisibility, setTicketVisibility] = useState("active");
  const [projectSection, setProjectSection] = useState("overview");
  const [confirmingArchive, setConfirmingArchive] = useState(false);
  const [editingArchiveReason, setEditingArchiveReason] = useState(false);
  const [archiveReason, setArchiveReason] = useState("");
  const [archiveReasonNote, setArchiveReasonNote] = useState("");
  const projectDetailRef = useRef(null);
  let previousBrowserDefault = null;
  try {
    previousBrowserDefault = Number(window.localStorage.getItem("atlas-current-project-id")
      ?? window.localStorage.getItem("atlas-default-project-id"));
  } catch { /* Browser storage is optional; the server owns the current default. */ }

  const allProjects = [...projects, ...archivedProjects];
  const isUnassignedView = selectedProjectId === "unassigned";
  const selectedProject = allProjects.find((project) => project.id === selectedProjectId);
  const isArchivedProject = Boolean(selectedProject?.archived_at);
  const unassignedTickets = tickets.filter((ticket) => ticket.project_id === null);
  const projectTicketSource = isArchivedProject ? archivedTickets : tickets;
  const selectedProjectTickets = isUnassignedView
    ? unassignedTickets
    : selectedProject
      ? projectTicketSource.filter((ticket) => ticket.project_id === selectedProject.id)
      : [];
  const visibleProjectTickets = ticketVisibility === "all" || isArchivedProject
    ? selectedProjectTickets
    : selectedProjectTickets.filter((ticket) => !TERMINAL_TICKET_STATUSES.has(ticket.status));
  const orderedVisibleProjectTickets = pinCurrentFocusTicket(
    visibleProjectTickets,
    isArchivedProject ? null : currentFocusTicketId,
  );

  function focusProjectDetail() {
    requestAnimationFrame(() => {
      const detailElement = projectDetailRef.current;
      const scrollPanel = detailElement?.closest(".main-content");
      if (!detailElement || !scrollPanel) return;
      const detailTop = scrollPanel.scrollTop + detailElement.getBoundingClientRect().top
        - scrollPanel.getBoundingClientRect().top;
      scrollPanel.scrollTop = detailTop;
    });
  }

  function selectProjectSection(section) {
    setProjectSection(section);
    focusProjectDetail();
  }

  function selectProject(projectId) {
    setConfirmingArchive(false);
    setEditingArchiveReason(false);
    setArchiveReason("");
    setArchiveReasonNote("");
    setTicketVisibility("active");
    setProjectSection("overview");
    onSelectProject(projectId);
  }

  async function confirmArchive() {
    if (!archiveReason || (archiveReason === "other" && !archiveReasonNote.trim())) return;
    const archived = await onArchiveProject?.(selectedProject, {
      archive_reason: archiveReason,
      archive_reason_note: archiveReasonNote.trim() || null,
    });
    if (archived) {
      setConfirmingArchive(false);
      setArchiveReason("");
      setArchiveReasonNote("");
    }
  }

  async function confirmArchiveClassification() {
    if (!archiveReason || (archiveReason === "other" && !archiveReasonNote.trim())) return;
    const classified = await onClassifyArchivedProject?.(selectedProject, {
      archive_reason: archiveReason,
      archive_reason_note: archiveReasonNote.trim() || null,
    });
    if (classified) {
      setEditingArchiveReason(false);
      setArchiveReason("");
      setArchiveReasonNote("");
    }
  }

  function openArchiveClassification() {
    setArchiveReason(selectedProject.archive_reason || "");
    setArchiveReasonNote(selectedProject.archive_reason_note || "");
    setEditingArchiveReason(true);
  }

  function closeArchiveDialog() {
    setConfirmingArchive(false);
    setEditingArchiveReason(false);
    setArchiveReason("");
    setArchiveReasonNote("");
  }

  function renderSelectedProject() {
    if (!selectedProject && !isUnassignedView) {
      return (
        <section className="project-selection-empty">
          <p className="eyebrow">PROJECT OVERVIEW</p>
          <h2>Choose a project to see its work.</h2>
          <p>The navigator keeps active work separate from preserved archived Projects.</p>
        </section>
      );
    }

    return (
      <section className={`project-detail${isArchivedProject ? " archived" : ""}`} ref={projectDetailRef}>
        <div className="project-detail-header">
          <div>
            <p className="eyebrow">{isUnassignedView ? "PROJECT OVERVIEW" : localProjectReference(selectedProject).toUpperCase()}</p>
            <div className="project-title-line">
              <h2>{isUnassignedView ? "Unassigned Work" : selectedProject.name}</h2>
              {isArchivedProject && (
                <span className="project-archived-label">
                  {projectArchiveReasonLabel(selectedProject.archive_reason)}
                </span>
              )}
            </div>
            <p>
              {isUnassignedView
                ? "Tickets without a project assignment remain available here."
                : `${selectedProjectTickets.length} ${selectedProjectTickets.length === 1 ? "ticket" : "tickets"} organized in this project.`}
            </p>
          </div>

          {!isUnassignedView && (
            <div className="project-detail-actions">
              <span className={`project-target-date ${selectedProject.target_date ? "" : "missing"}`}>
                {selectedProject.target_date ? `Target date: ${selectedProject.target_date}` : "No target date"}
              </span>
              <div className="project-header-buttons">
                <ProjectExportButton key={selectedProject.id} projectId={selectedProject.id} />
                {isArchivedProject ? (
                  <>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={projectArchivePending}
                      onClick={openArchiveClassification}
                    >
                      {selectedProject.archive_reason ? "Change Archive Reason" : "Set Archive Reason"}
                    </button>
                    <button
                      type="button"
                      className="secondary-button project-restore-button"
                      disabled={projectArchivePending}
                      onClick={() => onRestoreProject?.(selectedProject)}
                    >
                      {projectArchivePending ? "Restoring…" : "Restore Project"}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      className="secondary-button"
                      aria-label="Edit Project"
                      onClick={onEditProject}
                    >
                      <span className="project-action-label-full">Edit Project</span>
                      <span className="project-action-label-compact" aria-hidden="true">Edit</span>
                    </button>
                    <button
                      type="button"
                      className="secondary-button project-archive-button"
                      aria-label="Archive Project"
                      onClick={() => setConfirmingArchive(true)}
                    >
                      <span className="project-action-label-full">Archive Project</span>
                      <span className="project-action-label-compact" aria-hidden="true">Archive</span>
                    </button>
                    {onDefaultProjectChange && (
                      <button
                        type="button"
                        className="secondary-button"
                        aria-pressed={preferredProjectId === selectedProject.id}
                        title={preferredProjectId === selectedProject.id
                          ? "Clear this default project"
                          : "Use this project for new tickets across your devices"}
                        aria-label={savingDefaultProject ? "Saving Default Project" : preferredProjectId === selectedProject.id
                          ? "Default Project" : "Make Default Project"}
                        disabled={savingDefaultProject}
                        onClick={() => onDefaultProjectChange(
                          preferredProjectId === selectedProject.id ? null : selectedProject.id
                        )}
                      >
                        <span className="project-action-label-full">
                          {savingDefaultProject ? "Saving…" : preferredProjectId === selectedProject.id
                            ? "Default Project" : "Make Default Project"}
                        </span>
                        <span className="project-action-label-compact" aria-hidden="true">
                          {savingDefaultProject ? "Saving…" : "Default"}
                        </span>
                      </button>
                    )}
                  </>
                )}
              </div>
              {(defaultProjectError || projectArchiveError) && (
                <p role="alert">{defaultProjectError || projectArchiveError}</p>
              )}
              {!isArchivedProject && preferredProjectId == null
                && selectedProject.id === previousBrowserDefault && (
                <p className="muted">Previously this browser’s default. Choose Make Default Project to use it across devices.</p>
              )}
            </div>
          )}
        </div>

        {isArchivedProject && (
          <div className="project-archived-notice" role="status">
            <strong>Preserved and read-only</strong>
            <span>
              Archived as {projectArchiveReasonLabel(selectedProject.archive_reason)} on{" "}
              {formatLocalDateTime(selectedProject.archived_at)}. Its Tickets and history remain
              available, but changes require restoring the Project first.
              {selectedProject.archive_reason_note && (
                <span className="project-archive-reason-note">
                  {selectedProject.archive_reason_note}
                </span>
              )}
              <span>
                {selectedProject.archive_report_eligible_by_default
                  ? "Included in Activity Reports by default."
                  : "Excluded from Activity Reports by default unless explicitly included."}
              </span>
            </span>
          </div>
        )}

        {!isUnassignedView && (
          <nav
            className={`project-detail-tabs${isArchivedProject ? " archived" : ""}`}
            aria-label="Project sections"
          >
            <button
              type="button"
              aria-current={projectSection === "overview" ? "page" : undefined}
              onClick={() => selectProjectSection("overview")}
            >
              Project Overview
            </button>
            {!isArchivedProject && (
              <button
                type="button"
                aria-current={projectSection === "review" ? "page" : undefined}
                onClick={() => selectProjectSection("review")}
              >
                Telaryn AI Review
              </button>
            )}
            <button
              type="button"
              aria-current={projectSection === "history" ? "page" : undefined}
              onClick={() => selectProjectSection("history")}
            >
              Project History
            </button>
          </nav>
        )}

        {!isUnassignedView && !isArchivedProject && (
          <div hidden={projectSection !== "review"}>
            <ProjectReviewPanel
              key={selectedProject.id}
              project={selectedProject}
              tickets={selectedProjectTickets}
              onOpenTicket={onOpenTicket}
            />
          </div>
        )}

        {!isUnassignedView && projectSection === "history" && (
          <div className="project-history-stack">
            <ProjectLifecycle key={selectedProject.id} projectId={selectedProject.id} />
            <ProjectHistory
              projectId={selectedProject.id}
              onHistoryReady={focusProjectDetail}
              onOpenTicketById={(ticketId) => {
                const ticket = selectedProjectTickets.find((item) => item.id === ticketId);
                if (ticket) onOpenTicket(ticket);
              }}
            />
          </div>
        )}

        {(isUnassignedView || projectSection === "overview") && (
          <>
            {!isUnassignedView && <ProjectContextPanel project={selectedProject} />}
            {!isUnassignedView && (
              <ProjectWorkOverview
                projectId={selectedProject.id}
                onOpenTicketById={(ticketId) => {
                  const ticket = selectedProjectTickets.find((item) => item.id === ticketId);
                  if (ticket) onOpenTicket(ticket);
                }}
              />
            )}

            <div className="project-ticket-section">
              <div className="section-header">
                <div><p className="eyebrow">PROJECT WORK</p><h2>Tickets</h2></div>
                <div className="project-ticket-controls">
                  <span>{orderedVisibleProjectTickets.length}</span>
                  {!isArchivedProject && (
                    <div className="project-ticket-filter" aria-label="Ticket visibility">
                      <button type="button" aria-pressed={ticketVisibility === "active"} onClick={() => setTicketVisibility("active")}>Active</button>
                      <button type="button" aria-pressed={ticketVisibility === "all"} onClick={() => setTicketVisibility("all")}>All</button>
                    </div>
                  )}
                </div>
              </div>

              {selectedProjectTickets.length === 0 ? (
                <p className="muted">No tickets are assigned to this project.</p>
              ) : orderedVisibleProjectTickets.length === 0 ? (
                <p className="muted">No active tickets. Select All to view completed or cancelled work.</p>
              ) : (
                <div className="ticket-list">
                  {orderedVisibleProjectTickets.map((ticket) => {
                    const isCurrentFocus = !isArchivedProject && ticket.id === currentFocusTicketId;
                    return (
                      <article
                        className={`ticket-card${isCurrentFocus ? " current-focus" : ""}${isArchivedProject ? " archived" : ""}`}
                        data-current-focus={isCurrentFocus || undefined}
                        key={ticket.id}
                        onClick={() => onOpenTicket(ticket)}
                      >
                        <div className="ticket-meta">
                          <span>{localTicketReference(ticket)}</span>
                          <span>{ticket.ticket_type}</span>
                          {isArchivedProject && <span className="ticket-archived-list-indicator">Read-only</span>}
                          {ticket.ai_context_enabled === false && <span className="ticket-private-list-indicator">Private</span>}
                          {isCurrentFocus && <span className="ticket-focus-indicator">Current Focus</span>}
                        </div>
                        <div className="ticket-title-row">
                          <h3>{ticket.title}</h3>
                          <div className="ticket-inline-status">
                            <span className={`priority ${ticket.priority}`}>{ticket.priority}</span>
                            <span className="status-divider">•</span>
                            <span className={`ticket-status ${ticket.status}`}>{ticket.status.replace("_", " ")}</span>
                          </div>
                        </div>
                        {ticket.description && <p className="preserve-line-breaks">{ticket.description}</p>}
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
            {!isUnassignedView && <ProjectPublicReference project={selectedProject} />}
          </>
        )}

        {(confirmingArchive || editingArchiveReason) && (
          <div className="project-archive-dialog-backdrop" role="presentation">
            <section
              className="project-archive-dialog"
              role="dialog"
              aria-modal="true"
              aria-labelledby="archive-project-title"
            >
              <p className="eyebrow">
                {editingArchiveReason ? "ARCHIVE CLASSIFICATION" : "ARCHIVE PROJECT"}
              </p>
              <h2 id="archive-project-title">
                {editingArchiveReason
                  ? `Classify ${selectedProject.name}`
                  : `Archive ${selectedProject.name}?`}
              </h2>
              {editingArchiveReason ? (
                <>
                  <p>
                    Update how Telaryn understands this archived Project without restoring it or
                    unlocking its work.
                  </p>
                  <p className="muted">
                    The change will be added to Project History and immediately update its
                    default Activity Report eligibility.
                  </p>
                </>
              ) : (
                <>
                  <p>
                    Telaryn will remove this Project from active views, clear any saved default or
                    Current Focus tied to it, and preserve every Ticket and activity record.
                  </p>
                  <p className="muted">You can restore the Project later. Archived work is read-only.</p>
                </>
              )}
              <label className="project-archive-field">
                <span>
                  {editingArchiveReason
                    ? "How should this archived Project be classified?"
                    : "Why are you archiving this Project?"}
                </span>
                <select
                  value={archiveReason}
                  disabled={projectArchivePending}
                  onChange={(event) => setArchiveReason(event.target.value)}
                >
                  <option value="">Choose a reason</option>
                  {ARCHIVE_REASONS.filter((reason) => !reason.legacy).map((reason) => (
                    <option key={reason.value} value={reason.value}>{reason.label}</option>
                  ))}
                </select>
              </label>
              <label className="project-archive-field">
                <span>
                  Context {archiveReason === "other" ? "(required)" : "(optional)"}
                </span>
                <textarea
                  rows="3"
                  maxLength="1000"
                  value={archiveReasonNote}
                  disabled={projectArchivePending}
                  placeholder="Add context future-you will understand"
                  onChange={(event) => setArchiveReasonNote(event.target.value)}
                />
              </label>
              {projectArchiveError && <p className="criterion-error" role="alert">{projectArchiveError}</p>}
              <div className="project-archive-dialog-actions">
                <button
                  type="button"
                  className="secondary-button"
                  disabled={projectArchivePending}
                  onClick={closeArchiveDialog}
                >
                  {editingArchiveReason ? "Cancel" : "Keep Active"}
                </button>
                <button
                  type="button"
                  className="project-archive-confirm"
                  disabled={
                    projectArchivePending
                    || !archiveReason
                    || (archiveReason === "other" && !archiveReasonNote.trim())
                  }
                  onClick={editingArchiveReason ? confirmArchiveClassification : confirmArchive}
                >
                  {projectArchivePending
                    ? (editingArchiveReason ? "Saving…" : "Archiving…")
                    : (editingArchiveReason ? "Save Classification" : "Archive Project")}
                </button>
              </div>
            </section>
          </div>
        )}
      </section>
    );
  }

  return (
    <main className="main-content projects-page">
      <div className="topbar">
        <div><p className="eyebrow">PROJECTS</p><h1>See the bigger picture.</h1></div>
      </div>

      {projects.length === 0 && archivedProjects.length === 0 && unassignedTickets.length === 0 ? (
        <section className="project-empty-state">
          <h3>Create your first project.</h3>
          <p>Projects group related tickets so you can see progress and keep larger outcomes organized.</p>
          <button className="secondary-button" onClick={onCreateProject}>Create Project</button>
        </section>
      ) : (
        <div className="projects-workspace">
          <ProjectNavigator
            projects={projects}
            archivedProjects={archivedProjects}
            tickets={tickets}
            archivedTickets={archivedTickets}
            selectedProjectId={selectedProjectId}
            preferredProjectId={preferredProjectId}
            currentFocusProjectId={currentFocusProjectId}
            unassignedTickets={unassignedTickets}
            onSelectProject={selectProject}
            onCreateProject={onCreateProject}
          />
          <div className="project-detail-column">{renderSelectedProject()}</div>
        </div>
      )}
    </main>
  );
}

export default ProjectsView;

