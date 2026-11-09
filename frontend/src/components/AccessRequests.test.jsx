// Verify public intake confirmation and reviewer UI boundaries without real personal data.
import { beforeEach, expect, test, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccessRequestForm from "./AccessRequestForm";
import AccessRequestReview from "./AccessRequestReview";
import { submitAccessRequest, getIntakeReviewerAccess, getAccessRequests, getAccessRequest, issueInvitation } from "../api";

vi.mock("../api", () => ({ submitAccessRequest: vi.fn(), getIntakeReviewerAccess: vi.fn(), getAccessRequests: vi.fn(), getAccessRequest: vi.fn(), reviewAccessRequest: vi.fn(), issueInvitation: vi.fn(), revokeInvitation: vi.fn() }));
beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new Event("close")); };
});
test("submits minimal fields and gives a non-provisioning confirmation", async () => {
  submitAccessRequest.mockResolvedValue({ message: "Request received" });
  const user = userEvent.setup();
  render(<AccessRequestForm onClose={() => {}} />);
  await user.type(screen.getByLabelText("First name"), "Test");
  await user.type(screen.getByLabelText("Last name"), "Visitor");
  await user.type(screen.getByLabelText("Email address"), "test@example.com");
  await user.selectOptions(screen.getByLabelText(/How did you hear/), "github");
  await user.click(screen.getByRole("button", { name: "Submit Request" }));
  expect(submitAccessRequest).toHaveBeenCalledWith(expect.objectContaining({ email: "test@example.com", biography: "", phone: "", referral_source: "github" }));
  expect(await screen.findByRole("status")).toHaveTextContent("does not create an account or grant access");
  expect(screen.queryByLabelText("Email address")).not.toBeInTheDocument();
});
test("non-reviewers never load private requests", async () => {
  getIntakeReviewerAccess.mockResolvedValue({ allowed: false });
  render(<AccessRequestReview />);
  await waitFor(() => expect(getIntakeReviewerAccess).toHaveBeenCalled());
  expect(screen.queryByText("Load requests")).not.toBeInTheDocument();
  expect(getAccessRequests).not.toHaveBeenCalled();
});
test("authorized reviewers can load an empty queue", async () => {
  getIntakeReviewerAccess.mockResolvedValue({ allowed: true });
  getAccessRequests.mockResolvedValue({ items: [], total: 0, page: 1, pages: 1 });
  render(<AccessRequestReview />);
  expect(await screen.findByText("No requests match these filters.")).toBeInTheDocument();
  expect(screen.getByText("Previous")).toBeDisabled();
  expect(screen.getByText("Next")).toBeDisabled();
});

test("filters on the server and separates details from the queue", async () => {
  getIntakeReviewerAccess.mockResolvedValue({ allowed: true });
  const row = { id: 1, first_name: "Test", last_name: "Visitor", email: "test@example.com", status: "new", created_at: "2026-09-04T10:00:00Z" };
  getAccessRequests.mockResolvedValue({ items: [row], total: 1, page: 1, pages: 1 });
  getAccessRequest.mockResolvedValue({ ...row, expires_at: "2026-12-03T10:00:00Z", history: [] });
  const user = userEvent.setup();
  render(<AccessRequestReview />);
  await screen.findByText("test@example.com");
  await user.selectOptions(screen.getByLabelText("Status"), "");
  await waitFor(() => expect(getAccessRequests).toHaveBeenCalledWith({ status: null, search: "", page: 1 }));
  await user.type(screen.getByLabelText("Search name or email"), "Test");
  await user.click(screen.getByText("Apply filters"));
  await waitFor(() => expect(getAccessRequests).toHaveBeenLastCalledWith({ status: null, search: "Test", page: 1 }));
  await user.click(screen.getByRole("button", { name: "Open request from Test Visitor" }));
  expect(await screen.findByText("No review decisions yet.")).toBeInTheDocument();
  expect(screen.queryByLabelText("Search name or email")).not.toBeInTheDocument();
  await user.click(screen.getByText("← Back to requests"));
  expect(screen.getByLabelText("Search name or email")).toHaveValue("Test");
});

test("confirms when an activation link is copied", async () => {
  getIntakeReviewerAccess.mockResolvedValue({ allowed: true });
  const row = { id: 2, first_name: "Test", last_name: "Invitee", email: "invitee@example.com", status: "approved", created_at: "2026-09-04T10:00:00Z" };
  const detail = { ...row, expires_at: "2026-12-03T10:00:00Z", history: [], invitation: null };
  getAccessRequests.mockResolvedValue({ items: [row], total: 1, page: 1, pages: 1 });
  getAccessRequest.mockResolvedValue(detail);
  issueInvitation.mockResolvedValue({ activation_link: "http://localhost:5173/#/accept-invitation?token=safe-test-token" });
  const user = userEvent.setup();
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  render(<AccessRequestReview />);
  await user.click(await screen.findByRole("button", { name: "Open request from Test Invitee" }));
  await user.click(await screen.findByRole("button", { name: "Invite to create workspace" }));
  await user.click(screen.getByRole("button", { name: "Confirm and send invitation" }));
  await user.click(await screen.findByRole("button", { name: "Copy link" }));
  expect(writeText).toHaveBeenCalledWith("http://localhost:5173/#/accept-invitation?token=safe-test-token");
  expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
});
