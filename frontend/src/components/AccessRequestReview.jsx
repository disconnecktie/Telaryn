// Present a bounded reviewer queue separately from individual request details.
import { useEffect, useRef, useState } from "react";
import { getIntakeReviewerAccess, getAccessRequests, getAccessRequest, reviewAccessRequest, issueInvitation, revokeInvitation } from "../api";
import "./AccessRequests.css";

const statuses = ["new", "reviewed", "approved", "declined", "closed"];
const label = value => value.charAt(0).toUpperCase() + value.slice(1);
const date = value => new Date(value).toLocaleString();

export default function AccessRequestReview() {
  const [allowed, setAllowed] = useState(false);
  const [queue, setQueue] = useState(null);
  const [record, setRecord] = useState(null);
  const [draftStatus, setDraftStatus] = useState("new");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("new");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState({ status: "new", search: "", page: 1 });
  const heading = useRef(null);
  const queueLoadId = useRef(0);
  const [confirmingInvite, setConfirmingInvite] = useState(false);
  const [activationLink, setActivationLink] = useState("");
  const [copyState, setCopyState] = useState("idle");
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const access = await getIntakeReviewerAccess();
        if (!active) return;
        setAllowed(access.allowed);
        if (access.allowed) {
          const loadId = ++queueLoadId.current;
          const result = await getAccessRequests({ status: "new", search: "", page: 1 });
          if (active && loadId === queueLoadId.current) setQueue(result);
        }
      } catch (err) { if (active) setError(err.message); }
    }
    load();
    return () => { active = false; };
  }, []);
  async function run(operation) {
    if (busy) return;
    setBusy(true); setError("");
    try { await operation(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  async function loadQueue(next) {
    const loadId = ++queueLoadId.current;
    const result = await getAccessRequests(next);
    if (loadId !== queueLoadId.current) return;
    setQueue(result); setQuery({ ...next, page: result.page });
    window.dispatchEvent(new Event("atlas:intake-changed"));
  }
  if (!allowed) return null;
  return <section className="access-review" aria-label="Access request review" aria-busy={busy}>
    <h2 ref={heading} tabIndex={-1}>Access Requests</h2>
    <p>Review interest in Telaryn. Approval does not create an account or grant access.</p>
    {error && <p role="alert">{error}</p>}
    {record ? <article className="access-detail">
      <button disabled={busy} onClick={() => { setRecord(null); setConfirmingInvite(false); setActivationLink(""); setCopyState("idle"); heading.current?.focus(); }}>← Back to requests</button>
      <h3>{record.first_name} {record.last_name}</h3>
      <dl>{["email", "phone", "biography", "referral_source", "referral_detail", "notes", "created_at", "expires_at"].map(key => <div className={["biography", "notes"].includes(key) ? "access-detail-wide" : ""} key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{key.endsWith("_at") ? date(record[key]) : record[key] || "Not provided"}</dd></div>)}</dl>
      <div className="request-status-editor">
        <label>Request status<select value={draftStatus} disabled={busy} onChange={event => setDraftStatus(event.target.value)}>{statuses.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        <button type="button" disabled={busy || draftStatus === record.status} onClick={() => run(async () => {
          await reviewAccessRequest(record.id, draftStatus);
          window.dispatchEvent(new Event("atlas:intake-changed"));
          const updated = await getAccessRequest(record.id);
          setRecord(updated); setDraftStatus(updated.status);
          await loadQueue(query);
        })}>Save status</button>
        <span role="status">Saved status: <strong>{label(record.status)}</strong></span>
      </div>
      {record.status === "approved" && <section className="invitation-admin" aria-labelledby="invitation-heading">
        <h4 id="invitation-heading">Workspace invitation</h4>
        {record.invitation && <p>Status: <strong>{label(record.invitation.status)}</strong>{record.invitation.delivered_at ? ` · Sent ${date(record.invitation.delivered_at)}` : ""} · Expires {date(record.invitation.expires_at)}</p>}
        {!confirmingInvite && <div className="invitation-actions">
          {(!record.invitation || ["revoked", "expired", "delivery_failed"].includes(record.invitation.status)) && <button type="button" disabled={busy} onClick={() => setConfirmingInvite(true)}>{record.invitation ? "Send new invitation" : "Invite to create workspace"}</button>}
          {record.invitation?.status === "pending" && <>
            <button type="button" disabled={busy} onClick={() => setConfirmingInvite(true)}>Reissue invitation</button>
            <button type="button" disabled={busy} onClick={() => run(async () => {
              await revokeInvitation(record.id, record.invitation.generation);
              setActivationLink(""); setCopyState("idle"); setRecord(await getAccessRequest(record.id));
            })}>Revoke invitation</button>
          </>}
        </div>}
        {confirmingInvite && <div className="invitation-confirmation">
          <p><strong>Confirm invitation</strong></p>
          <p>Recipient: {record.first_name} {record.last_name} ({record.email})</p>
          <p>This invitation lets the recipient create an Telaryn account and a private workspace that they own. It does not add them to your workspace or grant intake-reviewer authority.</p>
          <button type="button" disabled={busy} onClick={() => run(async () => {
            const result = await issueInvitation(record.id, { expected_generation: record.invitation?.generation || null });
            setActivationLink(result.activation_link || ""); setCopyState("idle"); setConfirmingInvite(false); setRecord(await getAccessRequest(record.id));
          })}>Confirm and send invitation</button>
          <button type="button" disabled={busy} onClick={() => setConfirmingInvite(false)}>Cancel</button>
        </div>}
        {activationLink && <div className="activation-link" role="status">
          <p>This one-time local testing link is shown only now. Copy it before leaving this request.</p>
          <input aria-label="Activation link" readOnly value={activationLink} onFocus={event => event.target.select()} />
          <button type="button" disabled={copyState === "copying"} onClick={async () => {
            setCopyState("copying");
            try {
              if (!navigator.clipboard?.writeText) throw new Error("Clipboard access unavailable");
              await navigator.clipboard.writeText(activationLink);
              setCopyState("copied");
            } catch {
              setCopyState("failed");
            }
          }}>{copyState === "copied" ? "Copied" : copyState === "copying" ? "Copying…" : "Copy link"}</button>
          {copyState === "failed" && <p role="alert">Telaryn could not copy the link. Select the link above and copy it manually.</p>}
        </div>}
      </section>}
      <h4>History</h4>
      {record.history.length === 0 ? <p>No review decisions yet.</p> : <ul>{record.history.map((event, i) => <li key={i}>{label(event.previous_status)} → {label(event.status)} · {date(event.created_at)} · Reviewer {event.reviewer_id}</li>)}</ul>}
    </article> : <>
      <form className="access-queue-filters" onSubmit={event => { event.preventDefault(); run(() => loadQueue({ status: status || null, search: search.trim(), page: 1 })); }}>
        <label>Status<select value={status} disabled={busy} onChange={event => {
          const nextStatus = event.target.value;
          setStatus(nextStatus);
          run(() => loadQueue({ status: nextStatus || null, search: search.trim(), page: 1 }));
        }}><option value="">All statuses</option>{statuses.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        <label>Search name or email<input type="search" maxLength={100} value={search} disabled={busy} onChange={event => setSearch(event.target.value)} /></label>
        <button disabled={busy} type="submit">Apply filters</button>
        <button disabled={busy} type="button" onClick={() => run(() => loadQueue(query))}>Refresh</button>
      </form>
      {!queue && !error && <p role="status">Loading requests…</p>}
      {queue && <>
        <p role="status">{queue.total} matching requests · Page {queue.page} of {queue.pages}</p>
        {queue.items.length === 0 ? <p>No requests match these filters.</p> : <ul className="access-queue-list">{queue.items.map(row => <li key={row.id}>
          <div><strong>{row.first_name} {row.last_name}</strong><span>{row.email}</span></div>
          <span className="intake-count">{label(row.status)}</span>
          <time dateTime={row.created_at}>{date(row.created_at)}</time>
          <button disabled={busy} aria-label={`Open request from ${row.first_name} ${row.last_name}`} onClick={() => run(async () => { const detail = await getAccessRequest(row.id); setRecord(detail); setDraftStatus(detail.status); heading.current?.focus(); })}>Open</button>
        </li>)}</ul>}
        <nav aria-label="Request pages"><button disabled={busy || queue.page <= 1} onClick={() => run(() => loadQueue({ ...query, page: queue.page - 1 }))}>Previous</button><button disabled={busy || queue.page >= queue.pages} onClick={() => run(() => loadQueue({ ...query, page: queue.page + 1 }))}>Next</button></nav>
      </>}
    </>}
  </section>;
}

