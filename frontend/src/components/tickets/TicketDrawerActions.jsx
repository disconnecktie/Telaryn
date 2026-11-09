// Presents high-level drawer actions without owning status or AI orchestration.
import "./TicketDrawerActions.css";
import AtlasReviewProgress from "./AtlasReviewProgress";
import TicketExportMenu from "./TicketExportMenu";

function TicketDrawerActions({
  ticketId,
  canChangeStatus,
  canReview,
  reviewing,
  hasReviewError,
  onStartChangingStatus,
  onReview,
  onCancelReview,
}) {
  if (!ticketId && !canChangeStatus && !canReview) {
    return null;
  }

  return (
    <div className="drawer-actions">
      {ticketId && <TicketExportMenu ticketId={ticketId} />}
      {canChangeStatus && (
        <button className="secondary-button" onClick={onStartChangingStatus}>
          Change Status
        </button>
      )}

      {canReview && (reviewing ? (
        <AtlasReviewProgress onCancel={onCancelReview} compact />
      ) : (
        <button
          className="ai-button atlas-ai-review-button"
          onClick={onReview}
        >
          <>
            <span className="atlas-ai-review-icon" aria-hidden="true">
              ✨
            </span>
            <span>{hasReviewError ? "Retry Telaryn AI Review" : "Review w/ Telaryn AI"}</span>
          </>
        </button>
      ))}
    </div>
  );
}

export default TicketDrawerActions;

