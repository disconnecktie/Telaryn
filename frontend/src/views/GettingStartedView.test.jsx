// Verifies durable installation guidance remains available beyond the invitation email.
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import GettingStartedView from "./GettingStartedView";

test("explains how iPhone and Android users install the Telaryn web app", () => {
  render(<GettingStartedView signedIn onOpenWork={vi.fn()} />);

  expect(screen.getByRole("heading", { name: "Keep purposeful work one tap away." })).toBeInTheDocument();
  expect(screen.getByText("Visit telaryn.app using Safari on your iPhone.")).toBeInTheDocument();
  expect(screen.getByText("Select Add to Home Screen, then tap Add.")).toBeInTheDocument();
  expect(screen.getByText("Visit telaryn.app using Chrome on your Android phone.")).toBeInTheDocument();
  expect(screen.getByText("Choose Install app or Add to Home screen, then confirm.")).toBeInTheDocument();
  expect(screen.getByText(/Native iPhone and Android apps are planned/)).toBeInTheDocument();
});

test("uses the public Telaryn navigation before sign-in", () => {
  const onSignIn = vi.fn();
  const { container } = render(<GettingStartedView onSignIn={onSignIn} />);

  expect(container.querySelector("main")).toHaveClass("public-about-page");
  expect(screen.getByRole("link", { name: "Back to Telaryn" })).toHaveAttribute("href", "/");
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
  expect(onSignIn).toHaveBeenCalledOnce();
});
