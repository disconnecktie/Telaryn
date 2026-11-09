// Lets a person inspect and selectively approve AI proposals for an unsaved draft.
import { SuggestionBasisBadge, SuggestionBasisLegend } from "../SuggestionBasis";

const suggestionText = (item) => (typeof item === "string" ? item : item?.text || "");

function AtlasDraftReviewPanel({
  review,
  manualCriteria,
  manualSubtasks,
  reviewOptions,
  selectedCriteria,
  selectedSubtasks,
  selectedCriterionRevisions,
  selectedSubtaskRevisions,
  error,
  saving,
  onToggleReviewOption,
  onToggleCriterion,
  onToggleSubtask,
  onToggleCriterionRevision,
  onToggleSubtaskRevision,
  onBack,
  onCreate,
}) {
  const hasSuggestionBasis = [
    ...(review.recommendations || []),
    ...(review.acceptance_criteria || []),
    ...(review.suggested_subtasks || []),
    ...(review.acceptance_criteria_revisions || []),
    ...(review.subtask_revisions || []),
  ].some((item) => typeof item === "object" && item?.basis);

  return (
    <section className="draft-review-panel">
      <div className="ai-review-heading">
        <div>
          <p className="eyebrow">TELARYN DRAFT REVIEW</p>
          <h3>Choose what Telaryn should apply</h3>
        </div>

        <span className="ai-review-provider">{review.provider}</span>
      </div>

      {hasSuggestionBasis && <SuggestionBasisLegend />}

      {review.reasoning_summary && (
        <div className="review-summary">
          <span className="review-label">Why Telaryn suggests this</span>
          <p>{review.reasoning_summary}</p>
        </div>
      )}

      {(manualCriteria.length > 0 || manualSubtasks.length > 0) && (
        <div className="review-section">
          <span className="review-label">Already included from your draft</span>

          {manualCriteria.length > 0 && (
            <div className="draft-review-existing">
              <strong>Acceptance criteria</strong>
              <div className="draft-revision-list">
                {manualCriteria.map((criterion, index) => {
                  const revision = review.acceptance_criteria_revisions?.find(
                    (item) => item.source_index === index
                  );

                  return (
                    <div className="draft-revision-item" key={index}>
                      <p className="draft-original">{criterion}</p>
                      {revision && (
                        <label className="draft-revision-option">
                          <input
                            type="checkbox"
                            checked={selectedCriterionRevisions[index] || false}
                            onChange={() => onToggleCriterionRevision(index)}
                          />
                          <div>
                            <span className="review-label">
                              Use Telaryn revision
                            </span>
                            <SuggestionBasisBadge basis={revision.basis} />
                            <p>{revision.suggested_text}</p>
                            {revision.rationale && (
                              <small>{revision.rationale}</small>
                            )}
                          </div>
                        </label>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {manualSubtasks.length > 0 && (
            <div className="draft-review-existing">
              <strong>Subtasks</strong>
              <div className="draft-revision-list">
                {manualSubtasks.map((subtask, index) => {
                  const revision = review.subtask_revisions?.find(
                    (item) => item.source_index === index
                  );

                  return (
                    <div className="draft-revision-item" key={index}>
                      <p className="draft-original">{subtask.title}</p>
                      {revision && (
                        <label className="draft-revision-option">
                          <input
                            type="checkbox"
                            checked={selectedSubtaskRevisions[index] || false}
                            onChange={() => onToggleSubtaskRevision(index)}
                          />
                          <div>
                            <span className="review-label">
                              Use Telaryn revision
                            </span>
                            <SuggestionBasisBadge basis={revision.basis} />
                            <p>
                              <strong>{revision.suggested_title}</strong>
                            </p>
                            {revision.suggested_description && (
                              <p>{revision.suggested_description}</p>
                            )}
                            {revision.rationale && (
                              <small>{revision.rationale}</small>
                            )}
                          </div>
                        </label>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {review.suggested_title && (
        <label className="review-item">
          <input
            type="checkbox"
            checked={reviewOptions.apply_title}
            onChange={() => onToggleReviewOption("apply_title")}
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
            checked={reviewOptions.apply_description}
            onChange={() => onToggleReviewOption("apply_description")}
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
              checked={reviewOptions.apply_priority}
              onChange={() => onToggleReviewOption("apply_priority")}
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
              checked={reviewOptions.apply_ticket_type}
              onChange={() => onToggleReviewOption("apply_ticket_type")}
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
          <span className="review-label">Recommendations</span>
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
            Selected criteria will be added to the new ticket.
          </p>
        </div>
      )}

      {review.suggested_subtasks?.length > 0 && (
        <div className="review-section">
          <span className="review-label">Suggested subtasks</span>
          <div className="suggested-subtask-list">
            {review.suggested_subtasks.map((subtask, index) => (
              <label className="suggested-subtask selectable" key={index}>
                <input
                  type="checkbox"
                  checked={selectedSubtasks[index] || false}
                  onChange={() => onToggleSubtask(index)}
                />
                <div>
                  <SuggestionBasisBadge basis={subtask.basis} />
                  <strong>{subtask.title}</strong>
                  {subtask.description && <p>{subtask.description}</p>}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {error && <div className="ai-review-error">{error}</div>}

      <div className="modal-actions">
        <button className="secondary-button" onClick={onBack} disabled={saving}>
          Back to Draft
        </button>
        <button className="ai-button" onClick={onCreate} disabled={saving}>
          {saving ? "Creating..." : "Create Ticket & Selected Subtasks"}
        </button>
      </div>
    </section>
  );
}

export default AtlasDraftReviewPanel;

