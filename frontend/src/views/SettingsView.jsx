// Present browser-local theme preferences with an explicit exit back to work.
import "./SettingsView.css";
import ReleaseBadge from "../components/ReleaseBadge";
const THEME_OPTIONS = [
  {
    id: "dark",
    name: "Dark",
    description: "The original Telaryn look.",
  },
  {
    id: "light",
    name: "Light",
    description: "Bright, clean, and understated.",
  },
  {
    id: "kruszynko",
    name: "Kruszynko",
    description: "Warm, playful, and unmistakably pink.",
  },
];

function SettingsView({ theme, onThemeChange, onBackToWork }) {
  return (
    <main className="main-content settings-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">TELARYN SETTINGS</p>
          <h1>Make Telaryn yours.</h1>
        </div>
      </header>

      <section className="settings-section">
        <div>
          <h2>Theme</h2>
          <p className="muted">Choose how Telaryn looks on this browser.</p>
        </div>

        <div className="theme-grid">
          {THEME_OPTIONS.map((option) => (
            <button
              type="button"
              className={`theme-option ${option.id} ${
                theme === option.id ? "selected" : ""
              }`}
              key={option.id}
              onClick={() => onThemeChange(option.id)}
              aria-pressed={theme === option.id}
            >
              <span className="theme-preview" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
              <strong>{option.name}</strong>
              <span>{option.description}</span>
              {theme === option.id && <em>Selected</em>}
            </button>
          ))}
        </div>
      </section>

      <section className="settings-section settings-release" aria-labelledby="settings-release-heading">
        <div>
          <h2 id="settings-release-heading">Release</h2>
          <p className="muted">Use this version and build when contacting support.</p>
        </div>
        <ReleaseBadge showBuild />
        <p>© 2026 Jay Hughes. All rights reserved.</p>
      </section>

      {onBackToWork && (
        <button type="button" className="secondary-button settings-back-button" onClick={onBackToWork}>
          ← Back to My Work
        </button>
      )}
    </main>
  );
}

export default SettingsView;
