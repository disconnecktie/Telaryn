// Canonical Telaryn product story, shared by public visitors and authenticated workspace users.
import "./PublicLandingView.css";
import PublicHeader from "../components/PublicHeader";
import { useEffect, useState } from "react";
import { getIntakeAvailability } from "../api";
import AccessRequestForm from "../components/AccessRequestForm";
import PublicFooter from "../components/PublicFooter";
import ReleaseBadge from "../components/ReleaseBadge";

function PublicLandingView({ onSignIn, signedIn = false }) {
  const [intakeEnabled, setIntakeEnabled] = useState(false);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (signedIn) return undefined;

    let active = true;
    async function check() {
      try {
        const result = await getIntakeAvailability();
        if (active) setIntakeEnabled(result.enabled);
      } catch {
        // Keep sign-in usable when intake is unavailable.
      }
    }
    check();
    return () => { active = false; };
  }, [signedIn]);

  const pageClassName = signedIn
    ? "main-content public-landing public-about-page public-about-page--embedded"
    : "public-landing public-about-page";

  return (
    <main className={pageClassName}>
      {!signedIn && <PublicHeader onSignIn={onSignIn} />}

      <section className="public-hero public-about-hero">
        <p className="eyebrow">HUMAN-GOVERNED WORK INTELLIGENCE</p>
        <ReleaseBadge />
        <h1>Every action has a purpose.</h1>
        <p className="public-hero-copy">
          Telaryn turns incomplete requests, conversations, and context into
          structured, traceable work—while keeping every authoritative decision
          in human hands.
        </p>
        <p className="public-hero-principle">
          <strong>AI proposes. Humans approve. Telaryn records.</strong>{" "}
          Privacy protects every step.
        </p>
        {!signedIn && (
          <div className="public-hero-actions">
            <button className="public-primary-action" type="button" onClick={onSignIn}>
              Sign In to Your Workspace <span aria-hidden="true">→</span>
            </button>
            {intakeEnabled && (
              <button type="button" className="public-primary-action public-request-access" onClick={() => setRequesting(true)}>
                Request Access <span aria-hidden="true">→</span>
              </button>
            )}
          </div>
        )}
        {!signedIn && requesting && <AccessRequestForm onClose={() => setRequesting(false)} />}
      </section>

      <section className="public-principle-statement" aria-labelledby="problem-heading">
        <p className="eyebrow">THE PROBLEM</p>
        <h2 id="problem-heading">The work is real before the ticket is clear.</h2>
        <p>
          Important work begins in scattered messages, meetings, documents, and
          rough ideas. Telaryn reduces the translation burden between receiving
          information and knowing what to do next.
        </p>
      </section>

      <section className="public-what" aria-labelledby="what-heading">
        <p className="eyebrow">FROM CONTEXT TO ACTION</p>
        <h2 id="what-heading">Make the work clearer. Keep the why attached.</h2>
        <div className="public-what-grid">
          <article><span>01</span><h3>Capture what you know</h3><p>Begin with incomplete information and preserve the purpose, constraints, and evidence already available.</p></article>
          <article><span>02</span><h3>Shape it with intention</h3><p>Use bounded AI reviews to surface gaps, propose structure, and recommend a manageable next action.</p></article>
          <article><span>03</span><h3>Approve and trace</h3><p>Choose what becomes authoritative and retain a durable history of decisions, progress, and outcomes.</p></article>
        </div>
      </section>

      <section className="public-values" aria-labelledby="values-heading">
        <div>
          <p className="eyebrow">BUILT FOR TRUST</p>
          <h2 id="values-heading">AI assistance without surrendered authority.</h2>
        </div>
        <div className="public-values-grid">
          <article><h3>Human control</h3><p>Suggestions remain proposals until someone deliberately applies them.</p></article>
          <article><h3>Privacy by architecture</h3><p>Private context is excluded from AI workflows unless explicitly eligible and selected.</p></article>
          <article><h3>Operational clarity</h3><p>Provenance, activity history, and status records keep changes explainable.</p></article>
          <article><h3>Graceful independence</h3><p>Core work management remains useful when AI is disabled or unavailable.</p></article>
        </div>
      </section>

      <section className="public-current-build" aria-labelledby="current-build-heading">
        <div className="public-build-heading">
          <div><p className="eyebrow">CURRENT BUILD</p><h2 id="current-build-heading">Designed and engineered end to end.</h2></div>
          <p>A private, responsive application prepared for secure Azure staging.</p>
        </div>
        <dl className="public-stack">
          <div><dt>Experience</dt><dd>React + Vite · responsive desktop and mobile workflows</dd></div>
          <div><dt>Application API</dt><dd>FastAPI · explicit authorization and workflow boundaries</dd></div>
          <div><dt>Data</dt><dd>SQLAlchemy + Alembic · SQLite locally · PostgreSQL for deployment</dd></div>
          <div><dt>Platform</dt><dd>Docker · Azure Container Apps · Key Vault · Container Registry</dd></div>
          <div><dt>Identity</dt><dd>Workspace isolation · Microsoft Entra ID · managed identity</dd></div>
          <div><dt>Operations</dt><dd>Health checks · migration gates · privacy-safe diagnostics · recovery planning</dd></div>
          <div><dt>AI</dt><dd>Provider-agnostic, bounded review workflows with explicit human approval</dd></div>
          <div><dt>Quality</dt><dd>Automated frontend, backend, migration, infrastructure, and container validation</dd></div>
        </dl>
      </section>

      <section className="public-status" aria-label="Release availability">
        <strong>Release Candidate 1.</strong>
        <span>Telaryn is available to approved early-access workspace users.</span>
      </section>
      {!signedIn && <PublicFooter />}
    </main>
  );
}

export default PublicLandingView;
