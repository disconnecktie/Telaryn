// Verify Project exports download a Blob, remain user-triggered, and surface failures.
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { downloadProjectExport } from "../../api";
import ProjectExportButton from "./ProjectExportButton";

vi.mock("../../api", () => ({ downloadProjectExport: vi.fn() }));

describe("ProjectExportButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    URL.createObjectURL = vi.fn(() => "blob:project-export");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  test("downloads complete Project JSON only after an explicit click", async () => {
    downloadProjectExport.mockResolvedValue({
      blob: new Blob(['{"schema":"atlas.project-export"}'], { type: "application/json" }),
      filename: "prj-001-export.json",
    });

    render(<ProjectExportButton projectId={42} />);
    expect(downloadProjectExport).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Export Project JSON" }));

    await waitFor(() => expect(downloadProjectExport).toHaveBeenCalledWith(42));
    expect(URL.createObjectURL).toHaveBeenCalledOnce();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:project-export");
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce();
  });

  test("shows a safe inline error when export fails", async () => {
    downloadProjectExport.mockRejectedValue(new Error("Project not found"));

    render(<ProjectExportButton projectId={42} />);
    fireEvent.click(screen.getByRole("button", { name: "Export Project JSON" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Project not found");
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  test("disables button while an export request is pending", async () => {
    let resolve;
    downloadProjectExport.mockImplementation(() => new Promise((done) => { resolve = done; }));
    render(<ProjectExportButton projectId={42} />);
    const button = screen.getByRole("button", { name: "Export Project JSON" });
    fireEvent.click(button);
    expect(button).toBeDisabled();

    resolve({ blob: new Blob(["test"]), filename: "prj-001-export.json" });
    await waitFor(() => expect(button).not.toBeDisabled());
  });
});
