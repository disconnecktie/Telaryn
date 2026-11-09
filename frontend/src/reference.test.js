// Verifies human work keys stay distinct from internal database identity.
import { describe, expect, test } from "vitest";

import { localProjectReference } from "./projectReference";
import { localTicketReference } from "./ticketReference";

describe("human-facing work references", () => {
  test("formats workspace numbers as distinct padded Project and Ticket keys", () => {
    expect(localProjectReference({ id: 99, workspace_project_number: 4 })).toBe("PRJ-004");
    expect(localTicketReference({ id: 99, workspace_ticket_number: 28 })).toBe("TKT-028");
  });

  test("never presents a database row id as a collaboration reference", () => {
    expect(localProjectReference({ id: 99 })).toBe("PRJ-???");
    expect(localTicketReference({ id: 99 })).toBe("TKT-???");
  });
});
