// Keeps related ticket collections hidden until their initial requests have all settled.
function TicketDrawerRelatedContent({ ready, children }) {
  return (
    <div
      className={`ticket-drawer-related-content ${ready ? "ready" : "loading"}`}
      aria-busy={!ready}
    >
      {ready ? children : (
        <section className="ticket-drawer-loading-state" role="status" aria-live="polite">
          <div>
            <p className="detail-label">Ticket details</p>
            <p>Loading activity and planned work…</p>
          </div>
          <div className="ticket-drawer-loading-blocks" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        </section>
      )}
    </div>
  );
}

export default TicketDrawerRelatedContent;
