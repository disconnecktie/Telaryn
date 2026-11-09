// Protects browser-local rendering of authoritative UTC timestamp instants.
import { describe, expect, test } from "vitest";

import { formatLocalDateTime } from "./time";

describe("formatLocalDateTime", () => {
  test("renders the same UTC instant in the selected browser timezone", () => {
    const instant = "2026-01-15T13:00:00+00:00";

    expect(
      formatLocalDateTime(instant, {
        locale: "en-US",
        timeZone: "America/New_York",
      }),
    ).toContain("8:00 AM");
    expect(
      formatLocalDateTime(instant, {
        locale: "en-US",
        timeZone: "Europe/Berlin",
      }),
    ).toContain("2:00 PM");
  });

  test("does not require a timezone override in application use", () => {
    expect(formatLocalDateTime("2026-08-30T07:15:00Z")).not.toBe("Unknown time");
  });
});
