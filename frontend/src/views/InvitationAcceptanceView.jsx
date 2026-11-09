// Present a token-bound activation flow without placing invitation secrets in requests or logs.
import { useEffect, useState } from "react";
import { acceptExistingInvitation, activateNewAccount, inspectInvitation } from "../api";
import { AtlasBrand } from "../components/AtlasBrand";
import "../components/AccessRequests.css";

export default function InvitationAcceptanceView({ token, currentUser, onSignIn, onComplete }) {
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState("");
  useEffect(() => {
    let active = true;
    inspectInvitation(token).then(value => { if (active) setInvite(value); })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [token]);
  async function run(operation) {
    setBusy(true); setError("");
    try { setMessage((await operation()).message); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }
  return <main className="invitation-page">
    <section className="invitation-card" aria-busy={busy}>
      <AtlasBrand />
      <p className="eyebrow">WORKSPACE INVITATION</p>
      <h1>{invite ? "Create your Telaryn workspace" : "Telaryn invitation"}</h1>
      {busy && !invite && <p role="status">Checking invitation…</p>}
      {error && <p role="alert">{error}</p>}
      {invite && !message && <>
        <p>This invitation creates a private workspace that you own. It expires {new Date(invite.expires_at).toLocaleString()}.</p>
        <p className="invitation-account"><strong>Account email</strong><span>{invite.account_email}</span></p>
        {invite.requires_sign_in ? currentUser
          ? <button type="button" disabled={busy} onClick={() => run(() => acceptExistingInvitation(token))}>Accept with {currentUser.email}</button>
          : <><p>Sign in with the invited account to accept. Your existing password will not be changed.</p><button type="button" onClick={onSignIn}>Sign in to accept</button></>
          : <form onSubmit={event => { event.preventDefault(); run(() => activateNewAccount(token, password, confirmation)); }}>
              <label>Create password<input type="password" minLength={12} maxLength={1024} autoComplete="new-password" required value={password} onChange={event => setPassword(event.target.value)} /></label>
              <label>Confirm password<input type="password" minLength={12} maxLength={1024} autoComplete="new-password" required value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
              <p>Use at least 12 characters. Telaryn administrators cannot view your password.</p>
              <button type="submit" disabled={busy || password !== confirmation}>Activate account</button>
            </form>}
      </>}
      {message && <><p role="status">{message}</p><button type="button" onClick={onComplete}>{currentUser ? "Open Telaryn" : "Continue to sign in"}</button></>}
    </section>
  </main>;
}

