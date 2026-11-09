// Protect stable public routes, legacy links, and the routed sign-in boundary.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";
import RouterApp from "./RouterApp";

vi.mock("./App", () => ({
  default: () => <div>Telaryn application route</div>,
}));

function renderRoute(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <RouterApp />
    </MemoryRouter>
  );
}

test("keeps the established public landing presentation at its stable About route", () => {
  renderRoute("/about");
  expect(screen.getByRole("heading", { name: "Every action has a purpose." })).toBeInTheDocument();
  expect(screen.getByText("AI proposes. Humans approve. Telaryn records.")).toBeInTheDocument();
});

test("shares public navigation across established and journal pages", () => {
  renderRoute("/about");
  const publicNavigation = within(screen.getByRole("navigation", { name: "Public navigation" }));
  expect(publicNavigation.getByRole("link", { name: "Journal" })).toHaveAttribute("href", "/devlog");
  expect(publicNavigation.getByRole("link", { name: "Developer" })).toHaveAttribute("href", "/about-jay");
});

test("navigates between public pages inside the router", () => {
  renderRoute("/about");
  fireEvent.click(screen.getByRole("link", { name: "Privacy" }));
  expect(screen.getByRole("heading", { name: "Privacy should be understandable." })).toBeInTheDocument();
});

test("renders development journal entries by slug", () => {
  renderRoute("/devlog/why-i-built-telaryn");
  expect(screen.getByRole("heading", { name: "Why I Built Telaryn" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "← Engineering Journal" })).toHaveAttribute("href", "/devlog");
});

test("redirects legacy public hashes to stable routes", async () => {
  renderRoute("/#/privacy");
  expect(await screen.findByRole("heading", { name: "Privacy should be understandable." })).toBeInTheDocument();
});

test("renders the credential frame directly at the sign-in route", () => {
  renderRoute("/login");
  expect(screen.getByRole("heading", { name: "Welcome back." })).toBeInTheDocument();
  expect(screen.getByLabelText("Email")).toBeInTheDocument();
  expect(screen.getByLabelText("Password")).toBeInTheDocument();
});

test("opens the credential frame from the public header", () => {
  renderRoute("/about");
  fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
  expect(screen.getByRole("heading", { name: "Welcome back." })).toBeInTheDocument();
});

test("renders an intentional public fallback for unknown routes", () => {
  renderRoute("/missing-page");
  expect(screen.getByRole("heading", { name: "That page does not exist." })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Return to Telaryn" })).toHaveAttribute("href", "/");
});
