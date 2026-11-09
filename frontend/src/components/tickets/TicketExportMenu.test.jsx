// Protects JSON/PDF selection, browser download behavior, and safe failures.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { downloadTicketExport } from "../../api";
import TicketExportMenu from "./TicketExportMenu";

vi.mock("../../api", () => ({ downloadTicketExport: vi.fn() }));

describe("TicketExportMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => "blob:ticket-export");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  test.each([
    ["Machine-readable JSON", "json", "tkt-059-export.json"],
    ["Human-readable PDF", "pdf", "tkt-059-export.pdf"],
  ])("downloads %s", async (label, format, filename) => {
    downloadTicketExport.mockResolvedValue({ blob: new Blob(["export"]), filename });
    render(<TicketExportMenu ticketId={59} />);

    fireEvent.click(screen.getByText("Export"));
    fireEvent.click(screen.getByRole("menuitem", { name: new RegExp(label) }));

    await waitFor(() => expect(downloadTicketExport).toHaveBeenCalledWith(59, format));
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:ticket-export");
  });

  test("keeps a safe error visible when export fails", async () => {
    downloadTicketExport.mockRejectedValue(new Error("Ticket not found"));
    render(<TicketExportMenu ticketId={59} />);

    fireEvent.click(screen.getByText("Export"));
    fireEvent.click(screen.getByRole("menuitem", { name: /Machine-readable JSON/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ticket not found");
  });
});
