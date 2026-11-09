// Verify per-tab navigation recovery, workspace isolation, and safe storage failures.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readWorkspaceLocation, saveWorkspaceLocation, clearWorkspaceLocation } from "./workspaceLocation";

const user = { id: 1, workspace_id: 10 };
beforeEach(() => { window.sessionStorage.clear(); vi.restoreAllMocks(); });

describe("workspace location", () => {
  it("redirects a legacy Dashboard location to My Work", () => {
    saveWorkspaceLocation(user, { view: "dashboard", ticketId: 38 });
    expect(readWorkspaceLocation(user)).toMatchObject({ view: "work", ticketId: 38 });
  });
  it("restores the Reports destination", () => {
    saveWorkspaceLocation(user, { view: "reports" });
    expect(readWorkspaceLocation(user)).toMatchObject({ view: "reports" });
  });
  it("restores location without saving ticket contents or draft fields", () => {
    saveWorkspaceLocation(user, {
      view: "projects", ticketId: 38, projectId: 2, interruptedEdits: true,
      password: "never-store", draft: "private text",
    });
    expect(readWorkspaceLocation(user)).toEqual({
      view: "projects", ticketId: 38, projectId: 2, interruptedEdits: true,
    });
    const stored = window.sessionStorage.getItem("atlas-location:1:10");
    expect(stored).not.toContain("never-store");
    expect(stored).not.toContain("private text");
  });
  it("isolates users and workspaces", () => {
    saveWorkspaceLocation(user, { view: "work", ticketId: 38 });
    expect(readWorkspaceLocation({ id: 2, workspace_id: 10 })).toBeNull();
    expect(readWorkspaceLocation({ id: 1, workspace_id: 11 })).toBeNull();
    expect(readWorkspaceLocation(null)).toBeNull();
  });
  it("clears the saved ticket when the drawer closes", () => {
    saveWorkspaceLocation(user, { view: "work", ticketId: 38 });
    saveWorkspaceLocation(user, { view: "work" });
    expect(readWorkspaceLocation(user).ticketId).toBeNull();
  });
  it("removes the location on sign out", () => {
    saveWorkspaceLocation(user, { view: "work", ticketId: 38 });
    clearWorkspaceLocation(user);
    expect(readWorkspaceLocation(user)).toBeNull();
  });
  it("ignores malformed and unsupported locations", () => {
    window.sessionStorage.setItem("atlas-location:1:10", "{broken");
    expect(readWorkspaceLocation(user)).toBeNull();
    window.sessionStorage.setItem("atlas-location:1:10", '{"view":"unknown"}');
    expect(readWorkspaceLocation(user)).toBeNull();
  });
  it("does not let unavailable storage break navigation", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(readWorkspaceLocation(user)).toBeNull();
    expect(() => saveWorkspaceLocation(user, { view: "work" })).not.toThrow();
    expect(() => clearWorkspaceLocation(user)).not.toThrow();
  });
});
