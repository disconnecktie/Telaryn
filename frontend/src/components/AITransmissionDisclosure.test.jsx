// Verifies that no external AI action proceeds without an explicit user choice.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import AITransmissionDisclosure from "./AITransmissionDisclosure";

test("names the external transfer and requires explicit continuation", async () => {
  const user = userEvent.setup();
  const onCancel = vi.fn();
  const onContinue = vi.fn();

  render(
    <AITransmissionDisclosure
      open
      onCancel={onCancel}
      onContinue={onContinue}
    />,
  );

  expect(
    screen.getByText(/relevant non-private workspace context/i),
  ).toBeInTheDocument();
  expect(screen.getByText(/Classified or controlled information/i)).toBeInTheDocument();
  expect(screen.getByText(/Passwords, API keys/i)).toBeInTheDocument();
  expect(screen.getByText(/Sensitive personal or health information/i)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Continue with AI" }));
  expect(onContinue).toHaveBeenCalledOnce();
  expect(onCancel).not.toHaveBeenCalled();
});

test("supports cancelling without continuing", async () => {
  const user = userEvent.setup();
  const onCancel = vi.fn();
  const onContinue = vi.fn();

  render(
    <AITransmissionDisclosure
      open
      onCancel={onCancel}
      onContinue={onContinue}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onCancel).toHaveBeenCalledOnce();
  expect(onContinue).not.toHaveBeenCalled();
});
