// Verifies the browser-local AI consent window expires after 24 hours.
import { beforeEach, expect, test } from "vitest";

import {
  AI_ACKNOWLEDGMENT_TTL_MS,
  hasRecentAITransmissionAcknowledgment,
  recordAITransmissionAcknowledgment,
} from "./aiTransmissionAcknowledgment";

beforeEach(() => {
  window.localStorage.clear();
});

test("accepts an acknowledgment for less than 24 hours", () => {
  recordAITransmissionAcknowledgment(1000);
  expect(hasRecentAITransmissionAcknowledgment(1000 + AI_ACKNOWLEDGMENT_TTL_MS - 1)).toBe(true);
});

test("expires an acknowledgment at 24 hours", () => {
  recordAITransmissionAcknowledgment(1000);
  expect(hasRecentAITransmissionAcknowledgment(1000 + AI_ACKNOWLEDGMENT_TTL_MS)).toBe(false);
});

test("rejects missing, invalid, or future acknowledgments", () => {
  expect(hasRecentAITransmissionAcknowledgment(1000)).toBe(false);
  window.localStorage.setItem("atlas-ai-transmission-acknowledged-at", "invalid");
  expect(hasRecentAITransmissionAcknowledgment(1000)).toBe(false);
  recordAITransmissionAcknowledgment(2000);
  expect(hasRecentAITransmissionAcknowledgment(1000)).toBe(false);
});
