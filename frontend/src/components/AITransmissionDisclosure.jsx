// Requires explicit consent immediately before Telaryn sends content to an external AI provider.
import "./AITransmissionDisclosure.css";

function AITransmissionDisclosure({ open, onCancel, onContinue }) {
  if (!open) return null;

  return (
    <>
      <div className="ai-transmission-overlay" onClick={onCancel} />
      <section
        className="ai-transmission-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-transmission-title"
        aria-describedby="ai-transmission-description"
      >
        <p className="eyebrow">EXTERNAL AI PROVIDER</p>
        <h2 id="ai-transmission-title">Before you continue</h2>
        <p id="ai-transmission-description">
          Telaryn will send the information you entered and relevant non-private
          workspace context to the configured AI provider.
        </p>
        <div className="ai-transmission-warning">
          <strong>Do not include:</strong>
          <ul>
            <li>Classified or controlled information</li>
            <li>Passwords, API keys, or other credentials</li>
            <li>Sensitive personal or health information</li>
            <li>Anything your organization prohibits sharing with external AI</li>
          </ul>
        </div>
        <p className="ai-transmission-private-note">
          Projects and Tickets marked Private are excluded from AI context. After
          you continue, Telaryn will remember this acknowledgment in this browser
          for 24 hours.
        </p>
        <div className="ai-transmission-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="ai-button" onClick={onContinue} autoFocus>
            Continue with AI
          </button>
        </div>
      </section>
    </>
  );
}

export default AITransmissionDisclosure;

