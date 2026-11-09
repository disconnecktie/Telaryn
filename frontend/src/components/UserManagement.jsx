// Keep deployment administration metadata-only and distinct from workspace work.
import { useEffect, useRef, useState } from "react";
import {
  changeManagedWorkspaceRole, disableManagedUser, getManagedUser, getManagedUsers,
  reactivateManagedUser, removeManagedWorkspaceMembership, revokeManagedUserSessions,
} from "../api";
import "./UserManagement.css";

const title = value => value === "disabled" ? "Disabled" : "Active";

function Stat({ label, value }) {
  return <div className="managed-user-stat"><dt>{label}</dt><dd>{value}</dd></div>;
}

export default function UserManagement() {
  const [queue, setQueue] = useState(null);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("active");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState({ status: "active", search: "", page: 1 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const heading = useRef(null);

  async function load(next) {
    const result = await getManagedUsers(next);
    setQueue(result);
    setQuery({ ...next, page: result.page });
  }
  useEffect(() => {
    let active = true;
    getManagedUsers({ status: "active", search: "", page: 1 })
      .then(result => { if (active) { setQueue(result); setQuery({ status: "active", search: "", page: result.page }); } })
      .catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  }, []);
  async function run(operation) {
    if (busy) return;
    setBusy(true); setError("");
    try { await operation(); } catch (error) { setError(error.message); } finally { setBusy(false); }
  }
  async function open(id) {
    const detail = await getManagedUser(id);
    setSelected(detail);
    heading.current?.focus();
  }

  if (selected) return <section className="user-management" aria-busy={busy}>
    <button type="button" className="secondary-button user-management-back" onClick={() => setSelected(null)}>← All accounts</button>
    <header className="managed-user-hero">
      <div className="managed-user-avatar" aria-hidden="true">{selected.display_name.trim().charAt(0).toUpperCase()}</div>
      <div><p className="eyebrow">DEPLOYMENT ADMINISTRATION</p><h2 tabIndex={-1} ref={heading}>{selected.display_name}</h2><p className="user-management-email">{selected.email}</p></div>
      <span className={`managed-user-status ${selected.account_status}`}>{title(selected.account_status)}</span>
    </header>
    {error && <p className="user-management-alert" role="alert">{error}</p>}
    <dl className="managed-user-details">
      <Stat label="Account ID" value={selected.id} />
      <Stat label="Active sessions" value={selected.active_session_count} />
      <Stat label="Known sessions" value={selected.session_count} />
      <Stat label="Workspace access" value={selected.workspaces.length} />
      <Stat label="Account created" value={new Date(selected.created_at).toLocaleDateString()} />
    </dl>
    <section className="managed-workspaces">
      <div className="managed-section-heading"><div><p className="eyebrow">ACCESS</p><h3>Workspace memberships</h3></div><p>Only names and roles are visible here. Private work, tickets, updates, and AI context stay private.</p></div>
      {selected.workspaces.length ? <ul>{selected.workspaces.map(workspace => <li key={workspace.id}>
        <div className="managed-workspace-name"><strong>{workspace.name}</strong><span>Current role: {workspace.role}</span></div>
        <div className="managed-workspace-actions"><label>Role<select value={workspace.role} disabled={busy} onChange={event => {
          const role = event.target.value;
          if (window.confirm(`Change ${selected.display_name}'s role in ${workspace.name} to ${role}?`)) run(async () => setSelected(await changeManagedWorkspaceRole(selected.id, workspace.id, role)));
        }}><option value="owner">Owner</option><option value="member">Member</option></select></label>
        <button type="button" className="secondary-button" disabled={busy} onClick={() => {
          if (window.confirm(`Remove ${selected.display_name} from ${workspace.name}?`)) run(async () => setSelected(await removeManagedWorkspaceMembership(selected.id, workspace.id)));
        }}>Remove access</button></div>
      </li>)}</ul> : <p className="managed-empty-state">No workspace memberships.</p>}
    </section>
    <section className="managed-security">
      <div className="managed-section-heading"><div><p className="eyebrow">SECURITY</p><h3>Account controls</h3></div><p>Session revocation preserves the account. Disabling the account also ends every active session.</p></div>
      <div className="user-lifecycle-actions">
        <button type="button" className="secondary-button" disabled={busy || selected.active_session_count === 0} onClick={() => {
          if (window.confirm(`Revoke every active session for ${selected.display_name}? You will need to sign in again if this is your own account.`)) run(async () => setSelected(await revokeManagedUserSessions(selected.id)));
        }}>Revoke active sessions</button>
        {selected.account_status === "active" ? <button type="button" className="danger-button" disabled={busy} onClick={() => {
          if (window.confirm(`Disable ${selected.display_name}'s account and revoke all sessions?`)) run(async () => { setSelected(await disableManagedUser(selected.id)); await load(query); });
        }}>Disable account</button> : <button type="button" disabled={busy} onClick={() => {
          if (window.confirm(`Reactivate ${selected.display_name}'s account?`)) run(async () => { setSelected(await reactivateManagedUser(selected.id)); await load(query); });
        }}>Reactivate account</button>}
      </div>
    </section>
  </section>;

  return <section className="user-management" aria-busy={busy}>
    <header className="user-management-intro"><p className="eyebrow">DEPLOYMENT ADMINISTRATION</p><h2>User Management</h2><p>Manage account safety without opening private workspace content.</p></header>
    {error && <p className="user-management-alert" role="alert">{error}</p>}
    <form className="user-management-filters" onSubmit={event => { event.preventDefault(); run(() => load({ status, search: search.trim(), page: 1 })); }}>
      <label>Account status<select value={status} disabled={busy} onChange={event => setStatus(event.target.value)}><option value="active">Active</option><option value="disabled">Disabled</option><option value="all">All statuses</option></select></label>
      <label>Search name or email<input type="search" maxLength={100} value={search} disabled={busy} onChange={event => setSearch(event.target.value)} /></label>
      <button type="submit" disabled={busy}>Apply filters</button>
    </form>
    {!queue ? <p role="status">Loading accounts…</p> : <>
      <p className="managed-results" role="status">{queue.total} matching accounts <span>Page {queue.page} of {queue.pages}</span></p>
      {queue.items.length ? <ul className="managed-user-list">{queue.items.map(user => <li key={user.id}>
        <div className="managed-user-list-avatar" aria-hidden="true">{user.display_name.trim().charAt(0).toUpperCase()}</div>
        <div className="managed-user-list-identity"><strong>{user.display_name}</strong><span>{user.email}</span></div>
        <span className={`managed-user-status ${user.account_status}`}>{title(user.account_status)}</span>
        <span className="managed-user-workspaces">{user.workspace_count} workspace{user.workspace_count === 1 ? "" : "s"}</span>
        <button type="button" disabled={busy} onClick={() => run(() => open(user.id))}>Manage</button>
      </li>)}</ul> : <p className="managed-empty-state">No accounts match these filters.</p>}
      <nav className="user-management-pages" aria-label="User pages"><button type="button" disabled={busy || queue.page <= 1} onClick={() => run(() => load({ ...query, page: queue.page - 1 }))}>Previous</button><button type="button" disabled={busy || queue.page >= queue.pages} onClick={() => run(() => load({ ...query, page: queue.page + 1 }))}>Next</button></nav>
    </>}
  </section>;
}
