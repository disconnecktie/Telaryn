// Present the feedback-reviewer-only private queue and review workflow.
import { useEffect, useRef, useState } from "react";
import { getFeedbackDetail, getFeedbackQueue, getFeedbackScreenshot, updateFeedbackReview } from "../api";
import "../views/Feedback.css";

const label = value => value.charAt(0).toUpperCase() + value.slice(1);

export default function FeedbackAdministration() {
  const [queue, setQueue] = useState(null);
  const [selected, setSelected] = useState(null);
  const [state, setState] = useState("new");
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState({ state: "new", category: "all", search: "", page: 1 });
  const [reviewStatus, setReviewStatus] = useState("new");
  const [notes, setNotes] = useState("");
  const [imageUrl, setImageUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef(null);

  async function load(next) {
    const result = await getFeedbackQueue(next);
    setQueue(result); setQuery({ ...next, page: result.page });
  }
  useEffect(() => {
    let active = true;
    getFeedbackQueue(query).then(result => { if (active) setQueue(result); }).catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  // Initial administrator queue only.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!selected?.has_screenshot) return undefined;
    let active = true; let objectUrl;
    getFeedbackScreenshot(selected.reference).then(blob => {
      if (!active) return;
      objectUrl = URL.createObjectURL(blob); setImageUrl(objectUrl);
    }).catch(error => { if (active) setError(error.message); });
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [selected?.reference, selected?.has_screenshot]);

  async function run(operation) {
    if (busy) return;
    setBusy(true); setError("");
    try { await operation(); } catch (error) { setError(error.message); } finally { setBusy(false); }
  }
  async function open(reference) {
    const detail = await getFeedbackDetail(reference);
    setImageUrl(null);
    setSelected(detail); setReviewStatus(detail.status); setNotes(detail.admin_notes || "");
    window.requestAnimationFrame(() => heading.current?.focus());
  }
  async function saveReview(event) {
    event.preventDefault();
    await run(async () => {
      const detail = await updateFeedbackReview(selected.reference, { status: reviewStatus, admin_notes: notes.trim() || null });
      setSelected(detail); setReviewStatus(detail.status); setNotes(detail.admin_notes || "");
      await load(query);
    });
  }

  if (selected) return <section className="feedback-admin feedback-card" aria-busy={busy}>
    <button type="button" className="secondary-button feedback-back" onClick={() => { setSelected(null); setImageUrl(null); }}>← All feedback</button>
    <header className="feedback-admin-hero"><div><p className="eyebrow">FEEDBACK REVIEW</p><h1 tabIndex={-1} ref={heading}>{selected.reference}</h1><p>{label(selected.category)} · submitted {new Date(selected.created_at).toLocaleString()}</p></div><span className={`feedback-status ${selected.status}`}>{label(selected.status)}</span></header>
    {error && <p className="feedback-alert" role="alert">{error}</p>}
    <dl className="feedback-diagnostics">
      <div><dt>Submitted by</dt><dd>{selected.submitter.display_name}<span>{selected.submitter.email}</span></dd></div>
      <div><dt>Workspace</dt><dd>{selected.submitter.workspace_name}</dd></div>
      <div><dt>Page</dt><dd>{selected.route}</dd></div>
      <div><dt>Viewport</dt><dd>{selected.viewport_width && selected.viewport_height ? `${selected.viewport_width} × ${selected.viewport_height}` : "Unavailable"}</dd></div>
      <div><dt>App version</dt><dd>{selected.app_version}</dd></div>
      <div><dt>Browser</dt><dd className="feedback-browser">{selected.browser_context}</dd></div>
    </dl>
    <section className="feedback-original"><p className="eyebrow">ORIGINAL SUBMISSION</p><p className="preserve-line-breaks">{selected.description}</p></section>
    {selected.has_screenshot && <section className="feedback-screenshot"><p className="eyebrow">SCREENSHOT</p>{imageUrl ? <img src={imageUrl} alt={`Screenshot submitted with ${selected.reference}`} /> : <p role="status">Loading screenshot…</p>}<p>{selected.screenshot_filename} · {Math.ceil(selected.screenshot_size_bytes / 1024)} KB</p></section>}
    <form className="feedback-review" onSubmit={saveReview}>
      <label>Review status<select value={reviewStatus} disabled={busy} onChange={event => setReviewStatus(event.target.value)}><option value="new">New</option><option value="reviewing">Reviewing</option><option value="resolved">Resolved</option><option value="closed">Closed</option></select></label>
      <label>Review notes<textarea rows={5} maxLength={5000} value={notes} disabled={busy} onChange={event => setNotes(event.target.value)} placeholder="Record investigation details or the resolution." /></label>
      <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save Review"}</button>
    </form>
    {selected.events.length > 0 && <section className="feedback-history"><p className="eyebrow">REVIEW HISTORY</p><ol>{selected.events.map((event, index) => <li key={`${event.created_at}-${index}`}><strong>{label(event.previous_status)} → {label(event.new_status)}</strong><span>{event.actor_display_name} · {new Date(event.created_at).toLocaleString()}{event.notes_changed ? " · notes updated" : ""}</span></li>)}</ol></section>}
  </section>;

  return <section className="feedback-admin feedback-card" aria-busy={busy}>
    <header className="feedback-intro"><p className="eyebrow">FEEDBACK REVIEW</p><h1>User Feedback</h1><p>Review private reports without exposing them to workspace owners or other users.</p></header>
    {error && <p className="feedback-alert" role="alert">{error}</p>}
    <form className="feedback-filters" onSubmit={event => { event.preventDefault(); run(() => load({ state, category, search: search.trim(), page: 1 })); }}>
      <label>Status<select value={state} disabled={busy} onChange={event => setState(event.target.value)}><option value="new">New</option><option value="reviewing">Reviewing</option><option value="resolved">Resolved</option><option value="closed">Closed</option><option value="all">All</option></select></label>
      <label>Type<select value={category} disabled={busy} onChange={event => setCategory(event.target.value)}><option value="all">All</option><option value="problem">Problem</option><option value="suggestion">Suggestion</option><option value="other">Other</option></select></label>
      <label className="feedback-search">Search<input type="search" maxLength={100} value={search} disabled={busy} onChange={event => setSearch(event.target.value)} placeholder="Reference, description, or user" /></label>
      <button type="submit" disabled={busy}>Apply Filters</button>
    </form>
    {!queue ? <p role="status">Loading feedback…</p> : <>
      <p className="feedback-results" role="status">{queue.total} matching submissions <span>Page {queue.page} of {queue.pages}</span></p>
      {queue.items.length ? <ul className="feedback-list">{queue.items.map(item => <li key={item.reference}>
        <button type="button" disabled={busy} onClick={() => run(() => open(item.reference))}>
          <span className="feedback-list-top"><strong>{item.reference}</strong><span className={`feedback-status ${item.status}`}>{label(item.status)}</span></span>
          <span className="feedback-list-meta">{label(item.category)} · {item.submitter.display_name} · {new Date(item.created_at).toLocaleDateString()}{item.has_screenshot ? " · Screenshot" : ""}</span>
          <span className="feedback-list-preview">{item.description_preview}</span>
        </button>
      </li>)}</ul> : <p className="feedback-empty">No feedback matches these filters.</p>}
      <nav className="feedback-pages" aria-label="Feedback pages"><button type="button" disabled={busy || queue.page <= 1} onClick={() => run(() => load({ ...query, page: queue.page - 1 }))}>Previous</button><button type="button" disabled={busy || queue.page >= queue.pages} onClick={() => run(() => load({ ...query, page: queue.page + 1 }))}>Next</button></nav>
    </>}
  </section>;
}
