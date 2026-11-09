// Presents project health and attention signals without introducing AI judgment.
import { useEffect } from "react";
import { localTicketReference } from "../../ticketReference";
import useProjectWorkOverview from "../../hooks/useProjectWorkOverview";
import "./ProjectWorkOverview.css";

function ProgressRow({ label, progress }) {
  const percentage = progress.total
    ? Math.round((progress.completed / progress.total) * 100)
    : 0;

  return (
    <div className="project-progress-row">
      <div className="project-progress-copy">
        <strong>{label}</strong>
        <div className="project-progress-metrics" aria-label={`${label} progress details`}>
          <span><strong>{progress.completed}/{progress.total}</strong> Complete</span>
          <span><strong>{progress.total - progress.completed}</strong> Remaining</span>
          <span><strong>{progress.deferred}</strong> Deferred</span>
        </div>
      </div>
      <div
        className="project-progress-track"
        role="progressbar"
        aria-label={`${label} completion`}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={percentage}
      >
        <span style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

function HistoryList({ entries, onOpenTicketById }) {
  if (!entries.length) return <p className="muted">No recorded project changes yet.</p>;
  return <div className="project-history-list">{entries.map((entry) => (
    <button type="button" key={`${entry.event_type}-${entry.ticket_id}-${entry.occurred_at}`} onClick={() => onOpenTicketById(entry.ticket_id)}>
      <strong>{localTicketReference({ id: entry.ticket_id, workspace_ticket_number: entry.workspace_ticket_number })} {entry.ticket_title}</strong>
      <span>{entry.summary}</span>
      <small>
        <span>{new Date(entry.occurred_at).toLocaleDateString()}</span>
        <span>{new Date(entry.occurred_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
      </small>
    </button>
  ))}</div>;
}

export function ProjectHistory({ projectId, onHistoryReady, onOpenTicketById }) {
  const { overview, loading, error } = useProjectWorkOverview(projectId);

  useEffect(() => {
    if (!loading && overview) onHistoryReady?.();
  }, [loading, onHistoryReady, overview]);
  if (loading && !overview) return <p className="project-overview-state">Loading project history…</p>;
  if (error) return <p className="project-overview-state error">{error}</p>;
  const entries = overview?.recent_history || [];
  return (
    <section className="project-work-overview project-history-view" aria-labelledby="project-history-title">
      <div className="section-header project-overview-header">
        <div><p className="eyebrow">PROJECT HISTORY</p><h2 id="project-history-title">Recent Changes</h2></div>
        <span>{entries.length} recently updated tickets</span>
      </div>
      <HistoryList entries={entries} onOpenTicketById={onOpenTicketById} />
    </section>
  );
}

export default function ProjectWorkOverview({ projectId, onOpenTicketById }) {
  const { overview, loading, error } = useProjectWorkOverview(projectId);

  if (loading && !overview) {
    return <p className="project-overview-state">Building current snapshot…</p>;
  }

  if (error) {
    return <p className="project-overview-state error">{error}</p>;
  }

  if (!overview) return null;


  const summaryItems = [
    ["Active", overview.tickets.active],
    ["Blocked", overview.tickets.blocked],
    ["In Progress", overview.tickets.in_progress],
    ["Review", overview.tickets.review],
    ["Done", overview.tickets.done],
  ];

  return (
    <section className="project-work-overview" aria-labelledby="project-work-overview-title">
      <div className="section-header project-overview-header">
        <div>
          <h2 id="project-work-overview-title">Current Snapshot</h2>
        </div>
        <span>{overview.tickets.total} total tickets</span>
      </div>

      <div className="project-overview-counts">
        {summaryItems.map(([label, value]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>

      <div className="project-overview-body">
        <div className="project-progress-panel">
          <h3>Execution Progress</h3>
          <ProgressRow label="Acceptance Criteria" progress={overview.acceptance_criteria} />
          <ProgressRow label="Subtasks" progress={overview.subtasks} />
        </div>

        <div className="project-attention-panel">
          <div className="project-attention-heading">
            <h3>Needs Attention</h3>
            <span>{overview.attention.length}</span>
          </div>
          {overview.attention.length === 0 ? (
            <p className="muted">No active tickets currently need attention.</p>
          ) : (
            <div className="project-attention-list">
              {overview.attention.map((ticket) => (
                <button key={ticket.id} onClick={() => onOpenTicketById(ticket.id)}>
                  <span className="project-attention-ticket">{localTicketReference(ticket)} {ticket.title}</span>
                  <span className="project-attention-reasons">{ticket.reasons.join(" · ")}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
