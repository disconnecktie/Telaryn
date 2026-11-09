// Lock presentation surfaces to the one package-owned Telaryn release identity.
import { describe, expect, test } from "vitest";
import { TELARYN_RELEASE } from "./release";

describe("Telaryn release identity", () => {
  test("exposes the RC1 version and local build fallback", () => {
    expect(TELARYN_RELEASE).toMatchObject({
      version: "1.0.0-rc.1",
      displayVersion: "v1.0.0-rc.1",
      build: "development",
      shortBuild: "development",
      isReleaseCandidate: true,
    });
    expect(Object.isFrozen(TELARYN_RELEASE)).toBe(true);
  });
});
