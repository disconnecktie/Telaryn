// Owns drawer chrome and prevents accidental overlay/close interactions during edits.
function TicketDrawer({ children, editing, footer, hideClose = false, onClose }) {
  return (
    <>
      <div
        className="drawer-overlay"
        onClick={onClose}
      />

      <aside className={`ticket-drawer ${editing ? "editing" : ""}`}>
        {!hideClose && (
          <button
            className="close-button drawer-close-button"
            onClick={onClose}
            title="Close"
            aria-label="Close ticket"
          >
            ×
          </button>
        )}

        <div className="ticket-drawer-scroll">
          {children}
        </div>
        {footer}
      </aside>
    </>
  );
}

export default TicketDrawer;
