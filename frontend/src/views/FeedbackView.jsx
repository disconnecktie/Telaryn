// Collect private user feedback with explicit safety and diagnostic disclosure.
import { useEffect, useState } from "react";
import { submitFeedback } from "../api";
import "./Feedback.css";

const MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024;

export default function FeedbackView({ route = "/", onBack }) {
  const [category, setCategory] = useState("problem");
  const [description, setDescription] = useState("");
  const [screenshot, setScreenshot] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState(null);

  useEffect(() => {
    if (!screenshot) return undefined;
    let active = true;
    const reader = new FileReader();
    reader.addEventListener("load", () => { if (active) setPreview(reader.result); });
    reader.readAsDataURL(screenshot);
    return () => {
      active = false;
      if (reader.readyState === FileReader.LOADING) reader.abort();
    };
  }, [screenshot]);

  function chooseScreenshot(event) {
    const file = event.target.files?.[0] || null;
    setError(""); setPreview(null);
    if (file && file.size > MAX_SCREENSHOT_BYTES) {
      event.target.value = "";
      setScreenshot(null);
      setError("Choose a screenshot that is 5 MB or smaller.");
      return;
    }
    setScreenshot(file);
  }

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      setReceipt(await submitFeedback({
        category,
        description: description.trim(),
        route,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        screenshot,
      }));
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  if (receipt) return <main className="main-content feedback-page">
    <section className="feedback-card feedback-confirmation">
      <p className="eyebrow">FEEDBACK RECEIVED</p>
      <h1>Thank you for helping improve Telaryn.</h1>
      <p>Your feedback was submitted privately to an authorized feedback reviewer.</p>
      <div className="feedback-reference"><span>Reference</span><strong>{receipt.reference}</strong></div>
      <div className="feedback-actions">
        <button type="button" onClick={() => { setReceipt(null); setDescription(""); setScreenshot(null); }}>Send More Feedback</button>
        <button type="button" className="secondary-button" onClick={onBack}>Return to Telaryn</button>
      </div>
    </section>
  </main>;

  return <main className="main-content feedback-page">
    <section className="feedback-card">
      <header className="feedback-intro">
        <p className="eyebrow">PRIVATE FEEDBACK</p>
        <h1>Help us improve Telaryn.</h1>
        <p>Describe a problem or share an idea. Your submission is visible only to authorized feedback reviewers.</p>
      </header>
      <aside className="feedback-safety" aria-labelledby="feedback-safety-title">
        <strong id="feedback-safety-title">Before you submit</strong>
        <p>Do not include classified or controlled information, credentials, or unnecessarily sensitive personal or organizational information. Feedback is not sent to an AI provider.</p>
      </aside>
      {error && <p className="feedback-alert" role="alert">{error}</p>}
      <form className="feedback-form" onSubmit={submit}>
        <label>Feedback type<select value={category} disabled={busy} onChange={event => setCategory(event.target.value)}>
          <option value="problem">Problem</option><option value="suggestion">Suggestion</option><option value="other">Other</option>
        </select></label>
        <label>What would you like us to know?<textarea required minLength={10} maxLength={5000} rows={8} value={description} disabled={busy} onChange={event => setDescription(event.target.value)} placeholder="Describe what happened, what you expected, or what would make Telaryn better." /></label>
        <label className="feedback-file">Optional screenshot<input type="file" accept="image/png,image/jpeg,image/webp" disabled={busy} onChange={chooseScreenshot} /><span>PNG, JPEG, or WebP · 5 MB maximum</span></label>
        {screenshot && preview && <figure className="feedback-preview"><img src={preview} alt="Selected feedback screenshot preview" /><figcaption>{screenshot.name} · {Math.ceil(screenshot.size / 1024)} KB <button type="button" disabled={busy} onClick={() => { setScreenshot(null); setPreview(null); }}>Remove</button></figcaption></figure>}
        <details className="feedback-context"><summary>Technical context included</summary><p>Telaryn includes the current page, application version, browser, viewport size, submission time, your account, and your workspace so the reviewer can investigate.</p></details>
        <div className="feedback-actions">
          <button type="submit" disabled={busy || description.trim().length < 10}>{busy ? "Submitting…" : "Submit Feedback"}</button>
          <button type="button" className="secondary-button" disabled={busy} onClick={onBack}>Cancel</button>
        </div>
      </form>
    </section>
  </main>;
}
