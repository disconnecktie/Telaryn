// Presents an explicitly requested, advisory progress review after a committed update.
import "./TicketProgressReviewPanel.css";

export default function TicketProgressReviewPanel({ prompt, review, loading, applying, error,
  selected, onStart, onToggle, onApply, onDismiss }) {
  if (!prompt && !review && !loading && !error) return null;
  return <section className="ticket-progress-review" aria-label="Telaryn progress review">
    <div className="section-eyebrow">Optional Telaryn Review</div>
    {!review && <>
      <h3>Check this update against unfinished work?</h3>
      <p>Telaryn can compare only the update you just committed with incomplete Acceptance Criteria and Subtasks. Nothing changes unless you approve it.</p>
      {error && <div className="ai-review-error">{error}</div>}
      <div className="ticket-progress-review__actions">
        <button className="ai-button" onClick={onStart} disabled={loading}>{loading ? "Reviewing…" : "Review Progress with Telaryn"}</button>
        <button className="secondary-button" onClick={onDismiss} disabled={loading}>Not Now</button>
      </div>
    </>}
    {review && <>
      <h3>{review.suggestions.length ? "Telaryn found possible progress" : "No completion suggestions"}</h3>
      <p>{review.summary}</p>
      {review.suggestions.map(item => <label key={item.key} className="ticket-progress-review__suggestion">
        <input type="checkbox" checked={selected.includes(item.key)} disabled={item.state !== "available"} onChange={() => onToggle(item.key)} />
        <span><strong>{item.kind === "subtask" ? `Subtask ${item.reference_number}` : `Acceptance Criterion ${item.reference_number}`}: {item.text}</strong><small>{item.rationale}</small></span>
      </label>)}
      {error && <div className="ai-review-error">{error}</div>}
      <div className="ticket-progress-review__actions">
        {review.suggestions.length > 0 && <button className="ai-button" onClick={onApply} disabled={applying || selected.length === 0}>{applying ? "Applying…" : `Apply ${selected.length} Selected`}</button>}
        <button className="secondary-button" onClick={onDismiss} disabled={applying}>{review.suggestions.length ? "Reject Remaining" : "Close"}</button>
      </div>
    </>}
  </section>;
}

