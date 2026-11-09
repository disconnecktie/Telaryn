// Verifies Ticket Drawer focus movement, visibility checks, and reduced-motion behavior.
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  focusDrawerTarget,
  isDrawerTargetFullyVisible,
} from "./useDrawerTargetFocus";

function buildTarget({
  containerTop = 100,
  containerBottom = 500,
  targetTop = 160,
  targetBottom = 220,
} = {}) {
  const container = {
    getBoundingClientRect: () => ({
      top: containerTop,
      bottom: containerBottom,
    }),
  };
  const target = {
    closest: vi.fn(() => container),
    getBoundingClientRect: () => ({
      top: targetTop,
      bottom: targetBottom,
    }),
    scrollIntoView: vi.fn(),
    focus: vi.fn(),
  };
  return { container, target };
}

describe("drawer target focus navigation", () => {
  beforeEach(() => {
    window.matchMedia = vi.fn(() => ({ matches: false }));
  });

  it("focuses a visible target without changing the drawer scroll position", () => {
    const { target } = buildTarget();

    expect(isDrawerTargetFullyVisible(target)).toBe(true);
    focusDrawerTarget(target);

    expect(target.scrollIntoView).not.toHaveBeenCalled();
    expect(target.focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it("smoothly reveals an off-screen target before focusing it", () => {
    const { target } = buildTarget({ targetTop: 540, targetBottom: 600 });

    focusDrawerTarget(target);

    expect(target.scrollIntoView).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "nearest",
    });
    expect(target.focus).toHaveBeenCalledWith({ preventScroll: true });
  });

  it("uses immediate movement when reduced motion is preferred", () => {
    window.matchMedia = vi.fn(() => ({ matches: true }));
    const { target } = buildTarget({ targetTop: 540, targetBottom: 600 });

    focusDrawerTarget(target);

    expect(target.scrollIntoView).toHaveBeenCalledWith({
      behavior: "auto",
      block: "nearest",
    });
  });
});
