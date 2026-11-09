// Verify the optional mobile Settings exit invokes navigation without changing preferences.
import { render, screen, fireEvent } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import SettingsView from "./SettingsView";

test("returns to My Work through the explicit exit", () => {
  const back = vi.fn();
  const changeTheme = vi.fn();
  render(<SettingsView theme="dark" onThemeChange={changeTheme} onBackToWork={back} />);
  fireEvent.click(screen.getByRole("button", { name: /Back to My Work/ }));
  expect(back).toHaveBeenCalledOnce();
  expect(changeTheme).not.toHaveBeenCalled();
});
test("keeps the exit optional for desktop", () => {
  render(<SettingsView theme="dark" onThemeChange={vi.fn()} />);
  expect(screen.queryByRole("button", { name: /Back to My Work/ })).not.toBeInTheDocument();
});
