// Refresh reviewer-only counts without retaining intake data across signed-in identities.
import { useEffect, useState } from "react";
import { getIntakeReviewerAccess } from "../api";

export default function useIntakeNavigation(user) {
  const key = user ? `${user.id}:${user.workspace_id}` : null;
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!key) return undefined;
    let active = true;
    let generation = 0;
    async function refresh() {
      const request = ++generation;
      try {
        const result = await getIntakeReviewerAccess();
        if (active && request === generation) setState({ key, allowed: result.allowed, count: result.new_count ?? 0 });
      } catch {
        if (active && request === generation) setState({ key, allowed: false, count: 0 });
      }
    }
    function visible() { if (document.visibilityState === "visible") refresh(); }
    refresh();
    window.addEventListener("focus", refresh);
    window.addEventListener("atlas:intake-changed", refresh);
    document.addEventListener("visibilitychange", visible);
    return () => {
      active = false;
      window.removeEventListener("focus", refresh);
      window.removeEventListener("atlas:intake-changed", refresh);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [key]);
  return state?.key === key ? state : { allowed: false, count: 0 };
}
