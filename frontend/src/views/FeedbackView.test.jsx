// Protect private feedback disclosure, submission, and file-size behavior.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import { submitFeedback } from "../api";
import FeedbackView from "./FeedbackView";

vi.mock("../api", () => ({ submitFeedback: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks();
  submitFeedback.mockResolvedValue({ reference: "FBK-2222-3333-4444", status: "new", submitted_at: "2026-09-20T06:04:40Z" });
});

test("submits private feedback with bounded diagnostic context and confirms its reference", async () => {
  const user = userEvent.setup();
  render(<FeedbackView route="/app/projects?secret=no" onBack={vi.fn()} />);
  expect(screen.getByText(/not sent to an AI provider/i)).toBeInTheDocument();
  expect(screen.getByText(/application version, browser, viewport size/i)).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Feedback type"), "suggestion");
  await user.type(screen.getByLabelText("What would you like us to know?"), "Please make this workflow easier to discover.");
  await user.click(screen.getByRole("button", { name: "Submit Feedback" }));
  expect(submitFeedback).toHaveBeenCalledWith(expect.objectContaining({
    category: "suggestion",
    description: "Please make this workflow easier to discover.",
    route: "/app/projects?secret=no",
    screenshot: null,
  }));
  expect(await screen.findByText("FBK-2222-3333-4444")).toBeInTheDocument();
  expect(screen.getByText(/submitted privately/i)).toBeInTheDocument();
});

test("rejects an oversized screenshot before sending it", async () => {
  const user = userEvent.setup();
  render(<FeedbackView onBack={vi.fn()} />);
  const file = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "large.png", { type: "image/png" });
  await user.upload(screen.getByLabelText(/Optional screenshot/), file);
  expect(screen.getByRole("alert")).toHaveTextContent("5 MB or smaller");
  expect(submitFeedback).not.toHaveBeenCalled();
});
