// Verify the browser-side deadline and caller-controlled cancellation boundary.
import { afterEach, describe, expect, test, vi } from "vitest";

import { getTickets, login, resolveApiUrl, reviewTicketDraft, submitFeedback } from "./api";


function fetchUntilAborted() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((_url, options) => (
    new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        reject(new DOMException("Aborted", "AbortError"));
      });
    })
  ));
}


describe("AI review requests", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test("stops waiting after the browser-side deadline", async () => {
    vi.useFakeTimers();
    fetchUntilAborted();

    const review = reviewTicketDraft({ title: "Keep my draft" });
    const rejection = expect(review).rejects.toThrow("Your work is safe");
    await vi.advanceTimersByTimeAsync(50_000);

    await rejection;
  });

  test("allows a user to cancel without reporting a timeout", async () => {
    fetchUntilAborted();
    const controller = new AbortController();

    const review = reviewTicketDraft(
      { title: "Keep my draft" },
      { signal: controller.signal },
    );
    controller.abort();

    await expect(review).rejects.toThrow("was cancelled");
  });
});

describe("development API origin", () => {
  test("keeps localhost and 127.0.0.1 on one cookie site", () => {
    expect(resolveApiUrl("http://127.0.0.1:8000", {
      protocol: "http:",
      hostname: "localhost",
      origin: "http://localhost:5173",
    })).toBe("http://localhost:8000");
  });

  test("does not rewrite a configured non-loopback API host", () => {
    expect(resolveApiUrl("https://api.atlas.example", {
      protocol: "https:",
      hostname: "atlas.example",
      origin: "https://atlas.example",
    })).toBe("https://api.atlas.example");
  });
});


describe("safe API errors", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("keeps a rejected login on the form so its error remains visible", async () => {
    const unauthorized = vi.fn();
    window.addEventListener("atlas:unauthorized", unauthorized);
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 401,
      json: vi.fn().mockResolvedValue({ detail: "Invalid email or password." }),
    });

    try {
      await expect(login("tester.two@nope.com", "incorrect")).rejects.toThrow(
        "Invalid email or password.",
      );
      expect(unauthorized).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener("atlas:unauthorized", unauthorized);
    }
  });

  test("presents a server support reference without exposing internals", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
      json: vi.fn().mockResolvedValue({
        detail: "Telaryn encountered an unexpected error.",
        reference: "ATL-A1B2C3",
      }),
    });

    await expect(getTickets()).rejects.toThrow(
      "Telaryn encountered an unexpected error. Reference: ATL-A1B2C3",
    );
  });

  test("replaces browser network failures with an actionable safe message", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(getTickets()).rejects.toThrow(
      "Telaryn could not reach the server. Confirm the backend is running",
    );
  });

  test("preserves expected server workflow messages", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 409,
      json: vi.fn().mockResolvedValue({ detail: "The review snapshot changed." }),
    });

    await expect(getTickets()).rejects.toThrow("The review snapshot changed.");
  });
});

describe("private feedback uploads", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  test("lets the browser set the multipart boundary for FormData", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 201,
      json: vi.fn().mockResolvedValue({ reference: "FBK-TEST", status: "new" }),
    });

    await submitFeedback({
      category: "problem",
      description: "A reproducible mobile problem.",
      route: "/work",
      viewportWidth: 390,
      viewportHeight: 844,
    });

    const options = fetchMock.mock.calls[0][1];
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers).not.toHaveProperty("Content-Type");
  });
});

