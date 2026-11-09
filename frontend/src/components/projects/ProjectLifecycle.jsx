// Presents append-only Project archive and restore history.
import { useEffect, useState } from "react";
import { getProjectLifecycleEvents } from "../../api";
import { formatLocalDateTime } from "../../time";
import { projectArchiveReasonLabel } from "../../projectArchiveReasons";
import { projectLifeContextLabel } from "../../projectLifeContexts";

export default function ProjectLifecycle({ projectId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    getProjectLifecycleEvents(projectId)
      .then((items) => {
        if (active) setEvents(items);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  return (
    <section className="project-lifecycle" aria-labelledby="project-lifecycle-title">
      <div className="section-header">
        <div>
          <p className="eyebrow">PROJECT LIFECYCLE</p>
          <h2 id="project-lifecycle-title">Lifecycle History</h2>
        </div>
        <span>{events.length}</span>
      </div>
      {error && <p className="project-overview-state error">{error}</p>}
      {loading ? (
        <p className="muted">Loading lifecycle history…</p>
      ) : events.length === 0 ? (
        <p className="muted">No lifecycle changes have been recorded.</p>
      ) : (
        <ol>
          {events.map((event) => (
            <li key={event.id}>
              <span className={`project-lifecycle-marker ${event.action}`} aria-hidden="true" />
              <div>
                <strong>
                  {event.action === "life_context_changed"
                    ? `Life context changed · ${projectLifeContextLabel(event.previous_life_context)} → ${projectLifeContextLabel(event.new_life_context)}`
                    : event.action === "restored"
                    ? "Project restored"
                    : event.action === "archive_classified"
                      ? `Archive reason changed · ${projectArchiveReasonLabel(event.archive_reason)}`
                      : `Project archived · ${projectArchiveReasonLabel(event.archive_reason)}`}
                </strong>
                {event.archive_reason_note && <span>{event.archive_reason_note}</span>}
                <time dateTime={event.created_at}>{formatLocalDateTime(event.created_at)}</time>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
