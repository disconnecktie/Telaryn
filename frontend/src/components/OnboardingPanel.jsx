// Presents activity-derived first-run progress without creating or mutating work.
import "./OnboardingPanel.css";

const ACTIONS = {
  capture: "Capture your first piece of work",
  shape: "Learn how to refine and approve",
  focus: "Choose what matters now",
  record: "Record progress on your focus",
};

const OUTCOMES = {
  capture: "A Ticket you can act on",
  shape: "A clear definition of done",
  focus: "One priority in front of you",
  record: "A durable record of what happened",
};

export default function OnboardingPanel({ progress, onAction, onGuide, onDismiss }) {
  if (!progress?.show_panel) return null;
  const completedCount = progress.milestones.filter((item) => item.completed).length;
  const nextMilestone = progress.milestones.find((item) => !item.completed);
  return (
    <section className="onboarding-panel" aria-labelledby="onboarding-title">
      <header>
        <div>
          <p className="eyebrow">GETTING STARTED · {completedCount} OF 4</p>
          <h2 id="onboarding-title">
            {progress.completed ? "You completed the Telaryn loop." : "Put one piece of work through Telaryn."}
          </h2>
          <p>Four deliberate steps turn a rough idea into work you can trust. Telaryn helps; you decide.</p>
        </div>
        <button type="button" className="text-button" onClick={onDismiss}>Dismiss</button>
      </header>
      <ol className="onboarding-steps" aria-label="The Telaryn workflow">
        {progress.milestones.map((milestone, index) => (
          <li
            key={milestone.key}
            className={[
              milestone.completed ? "is-complete" : "",
              milestone.key === nextMilestone?.key ? "is-next" : "",
            ].filter(Boolean).join(" ")}
          >
            <span className="onboarding-step-marker" aria-hidden="true">{milestone.completed ? "✓" : index + 1}</span>
            <div className="onboarding-step-copy">
              <span className="onboarding-step-state">
                {milestone.completed ? "Done" : milestone.key === nextMilestone?.key ? "Next" : "Later"}
              </span>
              <strong>{milestone.label}</strong>
              <span className="onboarding-step-outcome">{OUTCOMES[milestone.key]}</span>
            </div>
          </li>
        ))}
      </ol>
      {nextMilestone ? (
        <div className="onboarding-next-action">
          <div>
            <span>YOUR NEXT STEP</span>
            <strong>{nextMilestone.label}</strong>
            <p>{nextMilestone.description}</p>
          </div>
          <button type="button" className="onboarding-action-button" onClick={() => onAction(nextMilestone.key)}>
            {ACTIONS[nextMilestone.key]} <span aria-hidden="true">→</span>
          </button>
        </div>
      ) : (
        <div className="onboarding-next-action is-finished">
          <div>
            <span>THE LOOP IS YOURS</span>
            <strong>Keep choosing deliberately.</strong>
            <p>Use the same rhythm whenever new work arrives.</p>
          </div>
        </div>
      )}
      <footer className="onboarding-footer">
        <span>Want the reasoning behind each step?</span>
        <button type="button" className="text-button" onClick={onGuide}>See how Telaryn works</button>
      </footer>
    </section>
  );
}
