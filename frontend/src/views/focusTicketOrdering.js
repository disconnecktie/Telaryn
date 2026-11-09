// Current Focus is a temporary presentation override. It reorders only the
// already-filtered result set and never mutates the authoritative ticket list.
export function pinCurrentFocusTicket(tickets, currentFocusTicketId) {
  if (!currentFocusTicketId) return tickets;

  const focusIndex = tickets.findIndex(
    (ticket) => ticket.id === currentFocusTicketId,
  );
  if (focusIndex <= 0) return tickets;

  return [
    tickets[focusIndex],
    ...tickets.slice(0, focusIndex),
    ...tickets.slice(focusIndex + 1),
  ];
}
