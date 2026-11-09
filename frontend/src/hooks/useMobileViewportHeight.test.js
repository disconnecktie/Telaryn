// Verifies mobile shell height recovery across visual-viewport and fallback measurements.
import { describe, expect, test } from "vitest";

import {
  mobileViewportHeight,
  syncMobileViewportHeight,
} from "./useMobileViewportHeight";

describe("mobile viewport height", () => {
  test("does not let a stale keyboard-reduced visual viewport shorten the shell", () => {
    expect(mobileViewportHeight({
      innerHeight: 844,
      visualViewport: { height: 510.4, offsetTop: 42.2 },
    })).toBe(844);
    expect(mobileViewportHeight({
      innerHeight: 844,
      visualViewport: { height: 510.4, offsetTop: 170 },
    })).toBe(844);
    expect(mobileViewportHeight({
      innerHeight: 510,
      visualViewport: { height: 510.4, offsetTop: 0 },
    })).toBe(510);
  });

  test("updates the shell custom property from the layout viewport fallback", () => {
    const style = {
      setProperty: (name, value) => {
        style[name] = value;
      },
    };
    syncMobileViewportHeight(
      { innerHeight: 844, visualViewport: null },
      { documentElement: { style } },
    );
    expect(style["--atlas-mobile-viewport-height"]).toBe("844px");
  });

  test("retains the pre-keyboard shell height when both viewport APIs shrink", () => {
    const style = {
      setProperty: (name, value) => {
        style[name] = value;
      },
    };
    const retainedHeight = syncMobileViewportHeight(
      { innerHeight: 510, visualViewport: { height: 510, offsetTop: 0 } },
      { documentElement: { style } },
      844,
    );
    expect(retainedHeight).toBe(844);
    expect(style["--atlas-mobile-viewport-height"]).toBe("844px");
  });
});
