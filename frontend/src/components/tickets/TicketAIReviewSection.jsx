// Displays persisted AI proposals; this component never applies them itself.
import { SuggestionBasisBadge, SuggestionBasisLegend } from "../SuggestionBasis";

const suggestionText = (item) => (typeof item === "string" ? item : item?.text || "");

function TicketAIReviewSection({
  review,
  error,
  options,
  selectedCriteria,
  applying,
  onToggleOption,
  onToggleCriterion,
  onDiscard,
  onApply,
}) {
  const hasSuggestionBasis = [
    ...(review?.recommendations || []),
    ...(review?.acceptance_criteria || []),
    ...(review?.suggested_subtasks || []),
  ].some((item) => typeof item === "object" && item?.basis);

  return (
    <>
      {error && <div className="ai-review-error">{error}</div>}

      {review && (
        <section className="ai-review-panel">
          <div className="ai-review-heading">
            <div>
              <p className="eyebrow">TELARYN AI REVIEW</p>
              <h3>Suggested improvements</h3>
            </div>
            <span className="ai-review-provider">{review.provider}</span>
          </div>

          {hasSuggestionBasis && <SuggestionBasisLegend />}

          {review.reasoning_summary && (
            <div className="review-summary">
              <span className="review-label">Why Telaryn flagged this</span>
              <p>{review.reasoning_summary}</p>
            </div>
          )}

          {review.suggested_title && (
            <label className="review-item">
              <input
                type="checkbox"
                checked={options.apply_title}
                onChange={() => onToggleOption("apply_title")}
              />
              <div>
                <span className="review-label">Title</span>
                <p>{review.suggested_title}</p>
              </div>
            </label>
          )}

          {review.suggested_description && (
            <label className="review-item">
              <input
                type="checkbox"
                checked={options.apply_description}
                onChange={() => onToggleOption("apply_description")}
              />
              <div>
                <span className="review-label">Description</span>
                <p>{review.suggested_description}</p>
              </div>
            </label>
          )}

          <div className="review-two-column">
            {review.suggested_priority && (
              <label className="review-item compact">
                <input
                  type="checkbox"
                  checked={options.apply_priority}
                  onChange={() => onToggleOption("apply_priority")}
                />
                <div>
                  <span className="review-label">Priority</span>
                  <p>{review.suggested_priority}</p>
                </div>
              </label>
            )}

            {review.suggested_ticket_type && (
              <label className="review-item compact">
                <input
                  type="checkbox"
                  checked={options.apply_ticket_type}
                  onChange={() => onToggleOption("apply_ticket_type")}
                />
                <div>
                  <span className="review-label">Type</span>
                  <p>{review.suggested_ticket_type}</p>
                </div>
              </label>
            )}
          </div>

          {review.missing_information?.length > 0 && (
            <div className="review-section">
              <span className="review-label">Missing / unclear information</span>
              <ul>
                {review.missing_information.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {review.recommendations?.length > 0 && (
            <div className="review-section">
              <span className="review-label">Recommended improvements</span>
              <div className="recommendation-list">
                {review.recommendations.map((recommendation, index) => (
                  <div className="recommendation-item" key={index}>
                    <SuggestionBasisBadge basis={recommendation.basis} />
                    <strong>{recommendation.text}</strong>
                    {recommendation.rationale && <p>{recommendation.rationale}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {review.acceptance_criteria?.length > 0 && (
            <div className="review-section">
              <span className="review-label">Suggested acceptance criteria</span>
              <div className="acceptance-list">
                {review.acceptance_criteria.map((criterion, index) => (
                  <label className="acceptance-item" key={index}>
                    <input
                      type="checkbox"
                      checked={selectedCriteria[index] || false}
                      onChange={() => onToggleCriterion(index)}
                    />
                    <span className="suggestion-content">
                      <SuggestionBasisBadge basis={criterion?.basis} />
                      {suggestionText(criterion)}
                    </span>
                  </label>
                ))}
              </div>
              <p className="review-note">
                Selected criteria will be added to the ticket.
              </p>
            </div>
          )}

          {review.suggested_subtasks?.length > 0 && (
            <div className="review-section">
              <label className="review-subtask-toggle">
                <input
                  type="checkbox"
                  checked={options.create_subtasks}
                  onChange={() => onToggleOption("create_subtasks")}
                />
                <span className="review-label">Create suggested subtasks</span>
              </label>
              <div className="suggested-subtask-list">
                {review.suggested_subtasks.map((subtask, index) => (
                  <div className="suggested-subtask" key={index}>
                    <SuggestionBasisBadge basis={subtask.basis} />
                    <strong>{subtask.title}</strong>
                    {subtask.description && <p>{subtask.description}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="ai-review-actions">
            <button className="secondary-button" onClick={onDiscard}>
              Discard
            </button>
            <button className="ai-button" onClick={onApply} disabled={applying}>
              {applying ? "Applying..." : "Apply Suggestions"}
            </button>
          </div>
        </section>
      )}
    </>
  );
}

export default TicketAIReviewSection;

