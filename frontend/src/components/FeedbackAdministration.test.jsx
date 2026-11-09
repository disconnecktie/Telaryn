// Protect feedback-reviewer access, private review, and lifecycle behavior.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { getFeedbackDetail, getFeedbackQueue, updateFeedbackReview } from "../api";
import FeedbackAdministration from "./FeedbackAdministration";

vi.mock("../api", () => ({
  getFeedbackDetail: vi.fn(),
  getFeedbackQueue: vi.fn(),
  getFeedbackScreenshot: vi.fn(),
  updateFeedbackReview: vi.fn(),
}));

const summary = { reference: "FBK-2222-3333-4444", category: "problem", status: "new", description_preview: "Drawer did not close", submitter: { display_name: "Jay", email: "jay@example.com", workspace_name: "Jay's Workspace" }, has_screenshot: false, created_at: "2026-09-20T06:04:40Z" };
const detail = { ...summary, description: "Drawer did not close after saving.", route: "/app/work", app_version: "0.1.0", viewport_width: 390, viewport_height: 844, browser_context: "Mobile Browser", screenshot_filename: null, screenshot_content_type: null, screenshot_size_bytes: null, admin_notes: null, reviewed_at: null, updated_at: summary.created_at, events: [] };

beforeEach(() => {
  vi.clearAllMocks();
  getFeedbackQueue.mockResolvedValue({ items: [summary], total: 1, page: 1, pages: 1 });
  getFeedbackDetail.mockResolvedValue(detail);
  updateFeedbackReview.mockResolvedValue({ ...detail, status: "reviewing", admin_notes: "Reproduced", events: [{ actor_display_name: "Telaryn Admin", actor_email: "admin@example.com", previous_status: "new", new_status: "reviewing", notes_changed: true, created_at: "2026-09-20T06:10:00Z" }] });
});

test("reviews private feedback and records an administrator disposition", async () => {
  const user = userEvent.setup();
  render(<FeedbackAdministration />);
  await user.click(await screen.findByRole("button", { name: /FBK-2222-3333-4444/ }));
  expect(await screen.findByText("Drawer did not close after saving.")).toBeInTheDocument();
  expect(screen.getByText("Jay's Workspace")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Review status"), "reviewing");
  await user.type(screen.getByLabelText("Review notes"), "Reproduced");
  await user.click(screen.getByRole("button", { name: "Save Review" }));
  expect(updateFeedbackReview).toHaveBeenCalledWith("FBK-2222-3333-4444", { status: "reviewing", admin_notes: "Reproduced" });
  expect(await screen.findByText("New → Reviewing")).toBeInTheDocument();
  expect(screen.getByText(/Telaryn Admin/)).toBeInTheDocument();
});
