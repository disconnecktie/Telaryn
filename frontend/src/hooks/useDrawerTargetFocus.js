// Coordinates visibility-aware focus movement for explicit Ticket Drawer workflows.
import { useLayoutEffect, useRef } from "react";

function prefersReducedMotion() {
  return typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function isDrawerTargetFullyVisible(target) {
  const scrollContainer = target?.closest?.(".ticket-drawer-scroll");
  if (!target || !scrollContainer) return true;

  const targetRect = target.getBoundingClientRect();
  const containerRect = scrollContainer.getBoundingClientRect();

  return targetRect.top >= containerRect.top
    && targetRect.bottom <= containerRect.bottom;
}

export function focusDrawerTarget(target) {
  if (!target) return;

  if (!isDrawerTargetFullyVisible(target)) {
    target.scrollIntoView({
      behavior: prefersReducedMotion() ? "auto" : "smooth",
      block: "nearest",
    });
  }

  target.focus({ preventScroll: true });
}

// Validation follows drawer DOM order: the first invalid control is the
// authoritative target when several failures are present.
export function useDrawerValidationFocus(error, containerRef) {
  useLayoutEffect(() => {
    if (!error) return undefined;

    const frame = window.requestAnimationFrame(() => {
      const target = containerRef.current?.querySelector('[aria-invalid="true"]')
        || containerRef.current?.querySelector('.criterion-error');
      focusDrawerTarget(target);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [error, containerRef]);
}

// Opening a drawer workflow owns focus movement. Routine edits, completion
// toggles, cancellation, and closing deliberately do not invoke this hook.
export default function useDrawerTargetFocus(active, targetRef, retrigger = null) {
  const wasActive = useRef(false);

  useLayoutEffect(() => {
    const opened = active && !wasActive.current;
    wasActive.current = active;

    if (!active || (!opened && !retrigger)) return undefined;

    const frame = window.requestAnimationFrame(() => {
      focusDrawerTarget(targetRef.current);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [active, retrigger, targetRef]);
}
