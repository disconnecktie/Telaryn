// Formats the workspace-scoped Ticket number as an intentional human work key.
export function localTicketReference(ticket) {
  const number = ticket?.workspace_ticket_number;
  return Number.isInteger(number) && number > 0
    ? `TKT-${String(number).padStart(3, "0")}`
    : "TKT-???";
}
