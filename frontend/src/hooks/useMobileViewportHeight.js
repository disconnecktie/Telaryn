// Keeps the mobile shell aligned with iOS's visual viewport after keyboard dismissal.
import { useEffect } from "react";

export function mobileViewportHeight(targetWindow = window) {
  const viewport = targetWindow.visualViewport;
  // iOS can retain a keyboard-reduced visual viewport after focus leaves the
  // field. The layout viewport remains the reliable lower bound for the shell.
  const measuredHeight = Math.max(
    Number.isFinite(viewport?.height) ? viewport.height : 0,
    Number.isFinite(targetWindow.innerHeight) ? targetWindow.innerHeight : 0,
  );
  if (!Number.isFinite(measuredHeight) || measuredHeight <= 0) {
    return Math.max(1, Math.round(targetWindow.innerHeight || 1));
  }
  return Math.round(measuredHeight);
}

export function syncMobileViewportHeight(
  targetWindow = window,
  targetDocument = document,
  minimumHeight = 0,
) {
  const height = Math.max(minimumHeight, mobileViewportHeight(targetWindow));
  targetDocument.documentElement.style.setProperty(
    "--atlas-mobile-viewport-height",
    `${height}px`,
  );
  return height;
}

function useMobileViewportHeight() {
  useEffect(() => {
    const viewport = window.visualViewport;
    let animationFrame = null;
    let settleTimer = null;
    let largestHeight = 0;

    function sync() {
      // Keyboard presentation may shrink both viewport APIs on iOS and leave
      // them stale after dismissal. Never replace the pre-keyboard shell
      // height with that smaller transient measurement.
      largestHeight = syncMobileViewportHeight(window, document, largestHeight);
    }

    function syncAfterViewportSettles() {
      sync();
      if (animationFrame !== null) window.cancelAnimationFrame(animationFrame);
      if (settleTimer !== null) window.clearTimeout(settleTimer);
      animationFrame = window.requestAnimationFrame(sync);
      settleTimer = window.setTimeout(sync, 300);
    }

    function resetAfterOrientationChange() {
      largestHeight = 0;
      syncAfterViewportSettles();
    }

    sync();
    window.addEventListener("resize", syncAfterViewportSettles);
    window.addEventListener("orientationchange", resetAfterOrientationChange);
    document.addEventListener("focusout", syncAfterViewportSettles);
    viewport?.addEventListener("resize", syncAfterViewportSettles);
    viewport?.addEventListener("scroll", syncAfterViewportSettles);

    return () => {
      window.removeEventListener("resize", syncAfterViewportSettles);
      window.removeEventListener("orientationchange", resetAfterOrientationChange);
      document.removeEventListener("focusout", syncAfterViewportSettles);
      viewport?.removeEventListener("resize", syncAfterViewportSettles);
      viewport?.removeEventListener("scroll", syncAfterViewportSettles);
      if (animationFrame !== null) window.cancelAnimationFrame(animationFrame);
      if (settleTimer !== null) window.clearTimeout(settleTimer);
      document.documentElement.style.removeProperty("--atlas-mobile-viewport-height");
    };
  }, []);
}

export default useMobileViewportHeight;
