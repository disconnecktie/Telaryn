// Verify new and existing recipients follow separate credential-safe activation paths.
import { beforeEach, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InvitationAcceptanceView from "./InvitationAcceptanceView";
import { acceptExistingInvitation, activateNewAccount, inspectInvitation } from "../api";

vi.mock("../api", () => ({ inspectInvitation: vi.fn(), activateNewAccount: vi.fn(), acceptExistingInvitation: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

test("new recipient confirms a twelve-character password", async () => {
  inspectInvitation.mockResolvedValue({ account_email: "new@example.com", workspace_name: "Your private workspace", role: "Workspace owner", requires_sign_in: false, expires_at: "2026-09-09T10:00:00Z" });
  activateNewAccount.mockResolvedValue({ message: "Account activated." });
  const user = userEvent.setup();
  render(<InvitationAcceptanceView token="secure-token" onSignIn={() => {}} onComplete={() => {}} />);
  expect(await screen.findByRole("heading", { name: "Create your Telaryn workspace" })).toBeInTheDocument();
  expect(screen.getByText("new@example.com")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Create password"), "long secure password");
  await user.type(screen.getByLabelText("Confirm password"), "long secure password");
  await user.click(screen.getByRole("button", { name: "Activate account" }));
  expect(activateNewAccount).toHaveBeenCalledWith("secure-token", "long secure password", "long secure password");
  expect(await screen.findByRole("status")).toHaveTextContent("Account activated");
});

test("existing recipient must sign in before acceptance", async () => {
  inspectInvitation.mockResolvedValue({ account_email: "new@example.com", workspace_name: "Your private workspace", role: "Workspace owner", requires_sign_in: true, expires_at: "2026-09-09T10:00:00Z" });
  const onSignIn = vi.fn();
  const user = userEvent.setup();
  render(<InvitationAcceptanceView token="secure-token" onSignIn={onSignIn} onComplete={() => {}} />);
  await user.click(await screen.findByRole("button", { name: "Sign in to accept" }));
  expect(onSignIn).toHaveBeenCalled();
  expect(activateNewAccount).not.toHaveBeenCalled();
});

test("signed-in invited account accepts without entering a password", async () => {
  inspectInvitation.mockResolvedValue({ account_email: "new@example.com", workspace_name: "Your private workspace", role: "Workspace owner", requires_sign_in: true, expires_at: "2026-09-09T10:00:00Z" });
  acceptExistingInvitation.mockResolvedValue({ message: "Invitation confirmed." });
  const user = userEvent.setup();
  render(<InvitationAcceptanceView token="secure-token" currentUser={{ email: "new@example.com" }} onSignIn={() => {}} onComplete={() => {}} />);
  await user.click(await screen.findByRole("button", { name: "Accept with new@example.com" }));
  expect(acceptExistingInvitation).toHaveBeenCalledWith("secure-token");
});

