// Collect public interest only; never persist drafts in browser storage or grant access.
import { useEffect, useRef, useState } from "react";
import { submitAccessRequest } from "../api";
import "./AccessRequests.css";

export default function AccessRequestForm({ onClose }) {
  const dialog = useRef(null);
  const [saving, setSaving] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  async function submit(event) {
    event.preventDefault();
    if (saving) return;
    const payload = Object.fromEntries(new FormData(event.currentTarget));
    setSaving(true);
    setError("");
    try {
      await submitAccessRequest(payload);
      setSent(true);
    } catch (err) { setError(err.message); }
    finally { setSaving(false); }
  }
  return <dialog ref={dialog} className="access-dialog" aria-labelledby="access-title" onCancel={(event) => { if (saving) event.preventDefault(); }} onClose={onClose}>
    <h2 id="access-title">Request Access</h2>
    {sent ? <div role="status"><p>Request received. This does not create an account or grant access.</p><p>We’ll review your interest and may contact you using the details provided.</p></div> : <form onSubmit={submit}>
      <p id="intake-privacy">We use this information only to understand interest and respond to your request, not for marketing or sale to third parties. Requests expire after 90 days and are removed from live storage by cleanup; backup copies age out separately. Please do not include sensitive information.</p>
      <p>Submitting does not create an account or grant access. Optional fields can be left blank.</p>
      <div className="access-fields">
        <label>First name<input name="first_name" autoComplete="given-name" required maxLength={100} /></label>
        <label>Last name<input name="last_name" autoComplete="family-name" required maxLength={100} /></label>
        <label>Email address<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
        <label>Phone number (optional)<input name="phone" type="tel" autoComplete="tel" maxLength={40} /></label>
      </div>
      <label>Brief biographical or professional context (optional)<textarea name="biography" maxLength={1000} rows={3} /></label>
      <label>How did you hear about Telaryn?<select name="referral_source" required defaultValue=""><option value="" disabled>Select one</option><option value="linkedin">LinkedIn</option><option value="friend">Friend or colleague</option><option value="search">Search engine</option><option value="github">GitHub</option><option value="other">Other</option></select></label>
      <label>Referral details / Other (optional)<input name="referral_detail" maxLength={200} /></label>
      <label>Additional notes (optional)<textarea name="notes" maxLength={1000} rows={3} /></label>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={saving}>{saving ? "Submitting…" : "Submit Request"}</button>
    </form>}
    <button type="button" onClick={() => dialog.current.close()} disabled={saving}>{sent ? "Back to About" : "Cancel"}</button>
  </dialog>;
}

