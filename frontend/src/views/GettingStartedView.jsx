// Explains Telaryn's human-governed work loop to public and signed-in users.
import PublicFooter from "../components/PublicFooter";
import PublicHeader from "../components/PublicHeader";
import "./GettingStartedView.css";

const STEPS = [
  ["Capture", "Start with the request as you received it. Telaryn can shape a rough note without creating anything behind your back."],
  ["Refine and approve", "Review the proposed Project or Ticket, answer only the useful questions, and approve the definition of done and next steps."],
  ["Execute", "Choose one Current Focus. Telaryn keeps alternatives visible without pretending everything is equally urgent."],
  ["Record", "Add progress and outcomes to the Ticket so the next decision starts with reliable context."],
];

export default function GettingStartedView({ signedIn = false, hasWork = true, progress, onSignIn, onOpenWork, onShowChecklist }) {
  return (
    <main className={`getting-started ${signedIn ? "is-signed-in main-content" : "is-public public-about-page"}${signedIn && !hasWork ? " is-empty-workspace" : ""}`}>
      {!signedIn && (
        <PublicHeader onSignIn={onSignIn} className="getting-started-public-nav" />
      )}
      <header className="getting-started-hero">
        <div className="getting-started-hero-copy">
          <p className="eyebrow">GETTING STARTED</p>
          <h1>This is how you use Telaryn.</h1>
          <p className="getting-started-lede">Bring in real work, make the plan yours, choose what matters now, and preserve what happened.</p>
          <div className="getting-started-actions">
            {signedIn ? (
              <>
                <button type="button" className="ai-button" onClick={onOpenWork}>Capture your first work</button>
                {progress?.dismissed && <button type="button" className="secondary-button" onClick={onShowChecklist}>Show checklist in My Work</button>}
              </>
            ) : <button type="button" className="ai-button" onClick={onSignIn}>Sign in to Telaryn</button>}
          </div>
        </div>
        {signedIn && !hasWork && (
          <aside className="getting-started-empty-cue">
            <span>YOUR WORKSPACE IS READY</span>
            <strong>Start with one real thing.</strong>
            <p>You do not need to design a whole system. Capture one request, decision, or outcome and let the loop show you the rest.</p>
          </aside>
        )}
      </header>
      <section className="getting-started-loop" aria-label="The Telaryn working loop">
        {STEPS.map(([title, body], index) => (
          <article key={title}>
            <span>{index + 1}</span><div><h2>{title}</h2><p>{body}</p></div>
          </article>
        ))}
      </section>
      <section className="getting-started-example">
        <div><p className="eyebrow">A USEFUL FIRST INPUT</p><h2>Specific enough to shape. Rough enough to improve.</h2></div>
        <blockquote>Plan a small community volunteer event for late October. I need to choose a venue, confirm a budget, recruit five volunteers, publish registration, and have a clear go/no-go decision two weeks before the event.</blockquote>
        <p>Telaryn proposes structure. You review and approve it. No Project, Ticket, criterion, or subtask is created automatically.</p>
      </section>
      <section className="getting-started-install" aria-labelledby="mobile-install-title">
        <div className="getting-started-install-intro">
          <p className="eyebrow">TELARYN ON YOUR PHONE</p>
          <h2 id="mobile-install-title">Keep purposeful work one tap away.</h2>
          <p>Add the Telaryn web app to your Home Screen for an app-like, full-screen experience—no download required.</p>
        </div>
        <div className="getting-started-install-platforms">
          <article>
            <div className="getting-started-install-platform"><span>iPhone</span><strong>Safari</strong></div>
            <ol className="getting-started-install-steps">
              <li><span>1</span><div><strong>Open Safari</strong><p>Visit telaryn.app using Safari on your iPhone.</p></div></li>
              <li><span>2</span><div><strong>Tap Share</strong><p>Use the Share button in Safari’s toolbar.</p></div></li>
              <li><span>3</span><div><strong>Add to Home Screen</strong><p>Select Add to Home Screen, then tap Add.</p></div></li>
            </ol>
          </article>
          <article>
            <div className="getting-started-install-platform"><span>Android</span><strong>Chrome</strong></div>
            <ol className="getting-started-install-steps">
              <li><span>1</span><div><strong>Open Chrome</strong><p>Visit telaryn.app using Chrome on your Android phone.</p></div></li>
              <li><span>2</span><div><strong>Open the menu</strong><p>Tap Chrome’s three-dot menu.</p></div></li>
              <li><span>3</span><div><strong>Install Telaryn</strong><p>Choose Install app or Add to Home screen, then confirm.</p></div></li>
            </ol>
          </article>
        </div>
        <p className="getting-started-install-note">Native iPhone and Android apps are planned as a future Telaryn release.</p>
      </section>
      {!signedIn && <PublicFooter />}
    </main>
  );
}
