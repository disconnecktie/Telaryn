// Keeps manual ticket creation and advisory draft review inside one modal boundary.
import { useState } from "react";

import AtlasDraftReviewPanel from "./AtlasDraftReviewPanel";
import NewTicketDraftForm from "./NewTicketDraftForm";

function NewTicketModal({
  review,
  recovered = false,
  guidedProgress = null,
  draftFormProps,
  reviewPanelProps,
  onClose,
  onSkipGuidedTicket,
  onEndGuidedReview,
}) {
  const [confirmingCancel, setConfirmingCancel] = useState(false);

  function requestClose() {
    if (guidedProgress) {
      setConfirmingCancel(true);
      return;
    }
    onClose();
  }

  function keepReviewing() {
    setConfirmingCancel(false);
  }

  function skipTicket() {
    setConfirmingCancel(false);
    onSkipGuidedTicket();
  }

  function endReview() {
    setConfirmingCancel(false);
    onEndGuidedReview();
  }

  return (
    <>
      <div className="modal-overlay" onClick={requestClose} />

      <div className="ticket-modal">
        <div className="modal-header">
          <div>
            <div className="new-ticket-heading-context">
              <p className="eyebrow">NEW TICKET</p>
              {guidedProgress && (
                <span className="guided-ticket-progress" role="status">
                  Ticket {guidedProgress.current} of {guidedProgress.total}
                </span>
              )}
            </div>
            <h2>What needs to get done?</h2>
          </div>

          <button
            type="button"
            className="close-button ticket-modal-close"
            onClick={requestClose}
            aria-label="Close ticket"
          >
            ×
          </button>
        </div>

        {confirmingCancel ? (
          <div className="guided-cancel-panel" role="dialog" aria-labelledby="guided-cancel-title">
            <h3 id="guided-cancel-title">What should happen to this proposal?</h3>
            <p>
              You can keep reviewing, skip only this Ticket, or end the remaining review.
              The Project and any Tickets already created will stay in place.
            </p>
            <div className="guided-cancel-actions">
              <button type="button" className="secondary-button" onClick={keepReviewing}>
                Keep Reviewing
              </button>
              <button type="button" className="secondary-button" onClick={skipTicket}>
                Skip This Ticket
              </button>
              <button type="button" className="danger-button" onClick={endReview}>
                End Review
              </button>
            </div>
          </div>
        ) : (
          <>
            {recovered && <p role="status">Manual draft restored from this browser tab. Nothing was created. Any AI review must be run again.</p>}
            {review ? (
              <AtlasDraftReviewPanel {...reviewPanelProps} review={review} />
            ) : (
              <NewTicketDraftForm {...draftFormProps} onCancel={requestClose} />
            )}
          </>
        )}
      </div>
    </>
  );
}

export default NewTicketModal;
