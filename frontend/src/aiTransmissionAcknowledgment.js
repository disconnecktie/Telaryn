// Keeps external-AI consent recent without treating it as permanent authorization.
const ACKNOWLEDGMENT_KEY = "atlas-ai-transmission-acknowledged-at";
export const AI_ACKNOWLEDGMENT_TTL_MS = 24 * 60 * 60 * 1000;

export function hasRecentAITransmissionAcknowledgment(now = Date.now()) {
  try {
    const acknowledgedAt = Number(window.localStorage.getItem(ACKNOWLEDGMENT_KEY));
    return Number.isFinite(acknowledgedAt)
      && acknowledgedAt > 0
      && now - acknowledgedAt >= 0
      && now - acknowledgedAt < AI_ACKNOWLEDGMENT_TTL_MS;
  } catch {
    return false;
  }
}

export function recordAITransmissionAcknowledgment(now = Date.now()) {
  try {
    window.localStorage.setItem(ACKNOWLEDGMENT_KEY, String(now));
  } catch {
    // The current request may proceed even when browser storage is unavailable.
  }
}
