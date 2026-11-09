// Verify draft expiry and workspace isolation without any server mutations.
import { beforeEach, expect, test } from "vitest";
import { saveNewTicketDraft, readNewTicketDraft, clearNewTicketDraft } from "./newTicketDraft";
const user = { id: 1, workspace_id: 1 };
const draft = { form: { title: "Draft", description: "" }, criteria: [], subtasks: [], criterionInput: "", subtaskInput: "" };
beforeEach(() => window.sessionStorage.clear());
test("drafts remain isolated by workspace and user", () => {
  saveNewTicketDraft(user, draft);
  expect(readNewTicketDraft(user).form.title).toBe("Draft");
  expect(readNewTicketDraft({ id: 2, workspace_id: 1 })).toBeNull();
  expect(readNewTicketDraft({ id: 1, workspace_id: 2 })).toBeNull();
  clearNewTicketDraft(user);
  expect(readNewTicketDraft(user)).toBeNull();
});
test("expired and malformed drafts are discarded", () => {
  window.sessionStorage.setItem("atlas-new-ticket:1:1", JSON.stringify({ ...draft, savedAt: Date.now() - 86400001 }));
  expect(readNewTicketDraft(user)).toBeNull();
  expect(window.sessionStorage.getItem("atlas-new-ticket:1:1")).toBeNull();
  window.sessionStorage.setItem("atlas-new-ticket:1:1", "broken");
  expect(readNewTicketDraft(user)).toBeNull();
});
