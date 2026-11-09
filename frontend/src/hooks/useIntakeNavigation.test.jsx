// Protect navigation counts across reviewer changes, refreshes, and account switches.
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { getIntakeReviewerAccess } from "../api";
import useIntakeNavigation from "./useIntakeNavigation";

vi.mock("../api", () => ({ getIntakeReviewerAccess: vi.fn() }));
beforeEach(() => vi.resetAllMocks());
test("refreshes count after review and clears access on signout", async () => {
  getIntakeReviewerAccess.mockResolvedValue({ allowed: true, new_count: 3 });
  const { result, rerender } = renderHook(({ user }) => useIntakeNavigation(user), { initialProps: { user: { id: 1, workspace_id: 1 } } });
  await waitFor(() => expect(result.current.count).toBe(3));
  getIntakeReviewerAccess.mockResolvedValue({ allowed: true, new_count: 2 });
  act(() => window.dispatchEvent(new Event("atlas:intake-changed")));
  await waitFor(() => expect(result.current.count).toBe(2));
  rerender({ user: null });
  expect(result.current.allowed).toBe(false);
  expect(result.current.count).toBe(0);
});
test("fails closed when the reviewer check fails", async () => {
  getIntakeReviewerAccess.mockRejectedValue(new Error("Unavailable"));
  const { result } = renderHook(() => useIntakeNavigation({ id: 2, workspace_id: 1 }));
  await waitFor(() => expect(getIntakeReviewerAccess).toHaveBeenCalled());
  expect(result.current.allowed).toBe(false);
});
