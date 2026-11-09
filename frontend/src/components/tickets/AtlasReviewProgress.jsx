// Presents a cancellable provider wait state without implying that work was applied.
import "./AtlasReviewProgress.css";
function AtlasReviewProgress({
  onCancel,
  compact = false,
  label = "Telaryn is reviewing",
  cancelLabel = "Cancel Review",
}) {
  return (
    <div
      className={`atlas-review-progress${compact ? " compact" : ""}`}
      role="status"
      aria-live="polite"
    >
      <span className="atlas-thinking-mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>

      <span className="atlas-review-progress-label">{label}</span>

      <button
        type="button"
        className="atlas-review-cancel-button"
        onClick={onCancel}
        aria-label={cancelLabel}
      >
        Cancel
      </button>
    </div>
  );
}

export default AtlasReviewProgress;

