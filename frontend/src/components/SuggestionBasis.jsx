// Presents the shared, non-authoritative basis vocabulary for AI suggestions.
import "./SuggestionBasis.css";

const BASIS_COPY = {
  supported: "Directly supported by the context you provided.",
  inferred: "A reasonable implication that was not stated directly.",
  recommended: "Optional guidance, not an authoritative requirement.",
};

export function SuggestionBasisBadge({ basis }) {
  if (!BASIS_COPY[basis]) return null;

  return (
    <span
      aria-hidden="true"
      className={`suggestion-basis suggestion-basis-${basis}`}
      title={BASIS_COPY[basis]}
    >
      {basis}
    </span>
  );
}

export function SuggestionBasisLegend() {
  return (
    <details className="suggestion-basis-legend">
      <summary>How Telaryn classified these suggestions</summary>
      <dl>
        {Object.entries(BASIS_COPY).map(([basis, description]) => (
          <div key={basis}>
            <dt><SuggestionBasisBadge basis={basis} /></dt>
            <dd>{description}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

