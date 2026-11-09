// Owns project-overview loading so the Projects view remains presentational.
import { useEffect, useState } from "react";

import { getProjectWorkOverview } from "../api";

export default function useProjectWorkOverview(projectId) {
  const [requestState, setRequestState] = useState({
    projectId: null,
    overview: null,
    error: "",
  });

  useEffect(() => {
    let active = true;

    if (!projectId) {
      return () => {
        active = false;
      };
    }

    getProjectWorkOverview(projectId)
      .then((result) => {
        if (active) {
          setRequestState({ projectId, overview: result, error: "" });
        }
      })
      .catch((requestError) => {
        if (active) {
          setRequestState({
            projectId,
            overview: null,
            error: requestError.message || "Unable to load project overview.",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [projectId]);

  if (!projectId) return { overview: null, loading: false, error: "" };
  if (requestState.projectId !== projectId) {
    return { overview: null, loading: true, error: "" };
  }
  return {
    overview: requestState.overview,
    loading: false,
    error: requestState.error,
  };
}
