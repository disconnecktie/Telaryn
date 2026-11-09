// Owns unified activity loading and human update entry outside the App coordinator.
import { useCallback, useRef, useState } from "react";
import { createTicketUpdate, getTicketActivity } from "../api";

function useTicketActivity() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const requestVersion = useRef(0);

  const reset = useCallback(() => {
    requestVersion.current += 1;
    setItems([]);
    setLoading(false);
    setError(null);
    setExpanded(false);
    setAdding(false);
    setDraft("");
    setSaving(false);
  }, []);

  const load = useCallback(async (ticketId, { preserveView = false } = {}) => {
    const requestId = requestVersion.current + 1;
    requestVersion.current = requestId;
    setLoading(true);
    setError(null);
    if (!preserveView) {
      setExpanded(false);
      setAdding(false);
      setDraft("");
    }

    try {
      const activity = await getTicketActivity(ticketId);
      if (requestVersion.current === requestId) {
        setItems(activity);
      }
      return activity;
    } catch (err) {
      if (requestVersion.current === requestId) {
        setError(err.message);
      }
      return null;
    } finally {
      if (requestVersion.current === requestId) {
        setLoading(false);
      }
    }
  }, []);

  const recordUpdate = useCallback(
    async (event, ticketId) => {
      event.preventDefault();
      const content = draft.trim();
      if (!content || saving) {
        return null;
      }

      setSaving(true);
      setError(null);
      try {
        const created = await createTicketUpdate(ticketId, { content });
        await load(ticketId, { preserveView: true });
        setDraft("");
        setAdding(false);
        return created;
      } catch (err) {
        setError(err.message);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [draft, load, saving]
  );

  const cancelAdding = useCallback(() => {
    setAdding(false);
    setDraft("");
    setError(null);
  }, []);

  const refresh = useCallback(
    (ticketId) => load(ticketId, { preserveView: true }),
    [load]
  );

  const startAdding = useCallback(() => setAdding(true), []);

  return {
    items,
    loading,
    error,
    expanded,
    adding,
    draft,
    saving,
    load,
    refresh,
    reset,
    setExpanded,
    startAdding,
    setDraft,
    cancelAdding,
    recordUpdate,
  };
}

export default useTicketActivity;
