// Centralizes browser-to-API translation so components stay focused on workflows.
export function resolveApiUrl(configuredUrl, browserLocation = window.location) {
  const fallback = `${browserLocation.protocol}//${browserLocation.hostname}:8000`;
  const resolved = new URL(configuredUrl || fallback, browserLocation.origin);
  const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1"]);

  // A cookie issued by 127.0.0.1 is not available to localhost (and vice
  // versa). Keep both development servers on the browser's chosen loopback
  // hostname even when an older .env uses the other spelling.
  if (loopbackHosts.has(resolved.hostname) && loopbackHosts.has(browserLocation.hostname)) {
    resolved.hostname = browserLocation.hostname;
  }

  return resolved.toString().replace(/\/$/, "");
}

const API_URL = resolveApiUrl(import.meta.env.VITE_API_URL);
const AI_REVIEW_TIMEOUT_MS = 50_000;

async function request(path, options = {}) {
  const { suppressUnauthorizedEvent = false, ...fetchOptions } = options;
  const hasFormBody = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      credentials: "include",
      headers: {
        ...(!hasFormBody && { "Content-Type": "application/json" }),
        ...fetchOptions.headers,
      },
      ...fetchOptions,
    });
  } catch (cause) {
    if (cause.name === "AbortError") throw cause;
    throw new Error(
      "Telaryn could not reach the server. Confirm the backend is running and try again.",
      { cause },
    );
  }

  if (!response.ok) {
    let detail = "Telaryn request failed.";
    let reference = null;

    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") detail = errorData.detail;
      if (typeof errorData.reference === "string") reference = errorData.reference;
    } catch {
      // Keep the generic safe message when the response is not JSON.
    }

    if (reference && !detail.includes(reference)) {
      detail = `${detail} Reference: ${reference}`;
    }
    const error = new Error(detail);
    error.status = response.status;
    error.reference = reference;
    if (response.status === 401 && !suppressUnauthorizedEvent) {
      window.dispatchEvent(new Event("atlas:unauthorized"));
    }
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

async function requestDownload(path, { entityLabel = "Ticket", defaultFilename = "ticket-export" } = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { credentials: "include" });
  } catch (cause) {
    throw new Error(
      "Telaryn could not reach the server. Confirm the backend is running and try again.",
      { cause },
    );
  }

  if (!response.ok) {
    let detail = `Telaryn could not export this ${entityLabel}.`;
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === "string") detail = errorData.detail;
    } catch {
      // Keep the safe export-specific message for non-JSON failures.
    }
    const error = new Error(detail);
    error.status = response.status;
    if (response.status === 401) window.dispatchEvent(new Event("atlas:unauthorized"));
    throw error;
  }

  const disposition = response.headers.get("Content-Disposition") || "";
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || defaultFilename;
  return { blob: await response.blob(), filename };
}

export function getCurrentSession() {
  return request("/auth/session");
}

export function getPreferences() {
  return request("/preferences/");
}

export function getOnboarding() {
  return request("/onboarding/");
}

export function updateOnboarding(dismissed) {
  return request("/onboarding/", {
    method: "PATCH",
    body: JSON.stringify({ dismissed }),
  });
}

export const getIntakeAvailability = () => request("/access-requests/availability");
export const getIntakeReviewerAccess = () => request("/access-requests/reviewer-access");
export const getDeploymentAdministratorAccess = () => request("/user-management/access");
export const getFeedbackReviewerAccess = () => request("/feedback/reviewer-access");
export const getManagedUsers = (query = {}) => {
  const params = new URLSearchParams(query);
  return request(`/user-management/users?${params}`);
};
export const getManagedUser = (id) => request(`/user-management/users/${id}`);
export const disableManagedUser = (id) => request(`/user-management/users/${id}/disable`, {
  method: "POST", body: JSON.stringify({ confirmed: true }),
});
export const reactivateManagedUser = (id) => request(`/user-management/users/${id}/reactivate`, {
  method: "POST", body: JSON.stringify({ confirmed: true }),
});
export const revokeManagedUserSessions = (id) => request(`/user-management/users/${id}/revoke-sessions`, {
  method: "POST", body: JSON.stringify({ confirmed: true }),
});
export const changeManagedWorkspaceRole = (userId, workspaceId, role) => request(`/user-management/users/${userId}/workspaces/${workspaceId}`, {
  method: "PATCH", body: JSON.stringify({ confirmed: true, role }),
});
export const removeManagedWorkspaceMembership = (userId, workspaceId) => request(`/user-management/users/${userId}/workspaces/${workspaceId}`, {
  method: "DELETE", body: JSON.stringify({ confirmed: true }),
});
export const submitFeedback = ({ category, description, route, viewportWidth, viewportHeight, screenshot }) => {
  const body = new FormData();
  body.append("category", category);
  body.append("description", description);
  body.append("route", route || "/");
  if (viewportWidth) body.append("viewport_width", String(viewportWidth));
  if (viewportHeight) body.append("viewport_height", String(viewportHeight));
  if (screenshot) body.append("screenshot", screenshot);
  return request("/feedback/", { method: "POST", body });
};
export const getFeedbackQueue = (query = {}) => {
  const params = new URLSearchParams(query);
  return request(`/feedback/admin?${params}`);
};
export const getFeedbackDetail = reference => request(`/feedback/admin/${reference}`);
export const updateFeedbackReview = (reference, payload) => request(`/feedback/admin/${reference}`, {
  method: "PATCH", body: JSON.stringify(payload),
});
export async function getFeedbackScreenshot(reference) {
  const response = await fetch(`${API_URL}/feedback/admin/${reference}/screenshot`, { credentials: "include" });
  if (!response.ok) {
    let detail = "Telaryn could not load this feedback screenshot.";
    try { detail = (await response.json()).detail || detail; } catch { /* Preserve safe fallback. */ }
    const error = new Error(detail);
    error.status = response.status;
    if (response.status === 401) window.dispatchEvent(new Event("atlas:unauthorized"));
    throw error;
  }
  return response.blob();
}
export const getAccessRequests = (query = {}) => request("/access-requests/queue", {
  method: "POST", body: JSON.stringify(query),
});
export const getAccessRequest = (id) => request(`/access-requests/${id}`);
export const reviewAccessRequest = (id, status) => request(`/access-requests/${id}`, {
  method: "PATCH", body: JSON.stringify({ status }),
});
export const issueInvitation = (requestId, payload) => request(`/access-requests/${requestId}/invitation`, {
  method: "POST", body: JSON.stringify(payload),
});
export const revokeInvitation = (requestId, expectedGeneration) => request(`/access-requests/${requestId}/invitation/revoke`, {
  method: "POST", body: JSON.stringify({ expected_generation: expectedGeneration }),
});
export const inspectInvitation = token => request("/access-requests/invitations/inspect", {
  method: "POST", body: JSON.stringify({ token }),
});
export const activateNewAccount = (token, password, passwordConfirmation) => request("/access-requests/invitations/accept-new", {
  method: "POST", body: JSON.stringify({ token, password, password_confirmation: passwordConfirmation }),
});
export const acceptExistingInvitation = token => request("/access-requests/invitations/accept-existing", {
  method: "POST", body: JSON.stringify({ token }),
});
export async function submitAccessRequest(payload) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 15000);
  try {
    return await request("/access-requests/", { method: "POST", body: JSON.stringify(payload), signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") throw new Error("Confirmation timed out. Your request may have been received; please wait before retrying.", { cause: error });
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

export function savePreferences(defaultProjectId) {
  return request("/preferences/", {
    method: "PUT",
    body: JSON.stringify({ default_project_id: defaultProjectId }),
  });
}

export function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    suppressUnauthorizedEvent: true,
  });
}

export function logout() {
  return request("/auth/session", { method: "DELETE" });
}

// Give ticket-level AI work a browser-side deadline while still allowing a user
// to cancel without closing the ticket or discarding its human-authored draft.
async function aiReviewRequest(path, body, externalSignal, cancelledMessage = "AI Review was cancelled. Your work is unchanged.") {
  const controller = new AbortController();
  let timedOut = false;
  const cancelFromCaller = () => controller.abort();

  if (externalSignal?.aborted) {
    controller.abort();
  } else {
    externalSignal?.addEventListener("abort", cancelFromCaller, { once: true });
  }

  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, AI_REVIEW_TIMEOUT_MS);

  try {
    return await request(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name !== "AbortError") throw error;
    if (timedOut) {
      throw new Error(
        "Telaryn AI did not respond in time. Your work is safe; retry when ready.",
        { cause: error },
      );
    }
    throw new Error(cancelledMessage, { cause: error });
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", cancelFromCaller);
  }
}

export function getTickets(includeArchived = false) {
  return request(`/tickets/${includeArchived ? "?include_archived=true" : ""}`);
}

export function getProjects(includeArchived = false) {
  return request(`/projects/${includeArchived ? "?include_archived=true" : ""}`);
}

export function getProjectLifecycleEvents(projectId) {
  return request(`/projects/${projectId}/lifecycle-events`);
}

export function archiveProject(projectId, archiveData) {
  return request(`/projects/${projectId}/archive`, {
    method: "POST",
    body: JSON.stringify(archiveData),
  });
}

export function classifyArchivedProject(projectId, archiveData) {
  return request(`/projects/${projectId}/archive-classification`, {
    method: "PUT",
    body: JSON.stringify(archiveData),
  });
}

export function restoreProject(projectId) {
  return request(`/projects/${projectId}/restore`, { method: "POST" });
}

export function getReportProjects() {
  return request("/activity-reports/projects");
}

export function generateActivityReport(configuration) {
  return request("/activity-reports/generate", {
    method: "POST",
    body: JSON.stringify(configuration),
  });
}

export function getMyWork() {
  return request("/my-work/");
}

export function updateMyWorkPreference(ticketId, preference) {
  return request(`/my-work/tickets/${ticketId}`, {
    method: "PATCH",
    body: JSON.stringify(preference),
  });
}

export function getProjectWorkOverview(projectId) {
  return request(`/projects/${projectId}/work-overview`);
}

export function getProjectReviewContext(projectId) {
  return request(`/projects/${projectId}/review-context`);
}

export function getProjectReviews(projectId) {
  return request(`/projects/${projectId}/reviews/`);
}

export function createProjectReview(projectId, { forceFresh = false } = {}) {
  const query = forceFresh ? "?force_fresh=true" : "";
  return request(`/projects/${projectId}/reviews/${query}`, { method: "POST" });
}

export function getProjectReviewDecisions(projectId, reviewId) {
  return request(`/projects/${projectId}/reviews/${reviewId}/decisions`);
}

export function getProjectReviewApplicationPreview(projectId, reviewId) {
  return request(`/projects/${projectId}/reviews/${reviewId}/application-preview`);
}

export function applyProjectReview(projectId, reviewId) {
  return request(`/projects/${projectId}/reviews/${reviewId}/apply`, {
    method: "POST",
  });
}

export function makeProjectReviewFocus(projectId, reviewId, proposalIndex) {
  return request(
    `/projects/${projectId}/reviews/${reviewId}/proposals/${proposalIndex}/make-focus`,
    { method: "POST" },
  );
}

export function undoProjectReviewFocus(projectId, reviewId, proposalIndex) {
  return request(
    `/projects/${projectId}/reviews/${reviewId}/proposals/${proposalIndex}/undo-focus`,
    { method: "POST" },
  );
}

export function saveProjectReviewDecision(projectId, reviewId, proposalIndex, decision) {
  return request(
    `/projects/${projectId}/reviews/${reviewId}/proposals/${proposalIndex}/decision`,
    {
      method: "PUT",
      body: JSON.stringify(decision),
    },
  );
}

export function getTicketStatusHistory(ticketId) {
  return request(`/tickets/${ticketId}/status-history`);
}

export function getTicketUpdates(ticketId) {
  return request(`/tickets/${ticketId}/updates/`);
}

export function getTicketActivity(ticketId) {
  return request(`/tickets/${ticketId}/activity`);
}

export function downloadTicketExport(ticketId, format) {
  if (!["json", "pdf"].includes(format)) {
    throw new Error("Choose JSON or PDF for the Ticket export.");
  }
  return requestDownload(`/tickets/${ticketId}/export.${format}`);
}

export function downloadProjectExport(projectId) {
  return requestDownload(`/projects/${projectId}/export.json`, {
    entityLabel: "Project",
    defaultFilename: "project-export.json",
  });
}

export function createTicketUpdate(ticketId, update) {
  return request(`/tickets/${ticketId}/updates/`, {
    method: "POST",
    body: JSON.stringify(update),
  });
}

export function createProject(project) {
  return request("/projects/", {
    method: "POST",
    body: JSON.stringify(project),
  });
}

export function updateProject(projectId, project) {
  return request(`/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify(project),
  });
}

export function updateProjectAIContextPolicy(projectId, aiContextEnabled) {
  return request(`/projects/${projectId}/ai-context-policy`, {
    method: "PATCH",
    body: JSON.stringify({ ai_context_enabled: aiContextEnabled }),
  });
}

export function getSubtasks(ticketId) {
  return request(`/tickets/${ticketId}/subtasks/`);
}

export function getAcceptanceCriteria(ticketId) {
  return request(`/tickets/${ticketId}/acceptance-criteria/`);
}

export function createAcceptanceCriterion(ticketId, criterion) {
  return request(`/tickets/${ticketId}/acceptance-criteria/`, {
    method: "POST",
    body: JSON.stringify(criterion),
  });
}

export function saveAcceptanceCriteria(ticketId, criteria) {
  return request(`/tickets/${ticketId}/acceptance-criteria/`, {
    method: "PUT",
    body: JSON.stringify({ criteria }),
  });
}

export function updateAcceptanceCriterion(
  ticketId,
  criterionId,
  updates
) {
  return request(
    `/tickets/${ticketId}/acceptance-criteria/${criterionId}`,
    {
      method: "PATCH",
      body: JSON.stringify(updates),
    }
  );
}

export function deleteAcceptanceCriterion(ticketId, criterionId) {
  return request(`/tickets/${ticketId}/acceptance-criteria/${criterionId}`, {
    method: "DELETE",
  });
}

export function createAIReview(ticketId, { signal } = {}) {
  return aiReviewRequest(`/tickets/${ticketId}/ai-reviews/`, undefined, signal);
}

export function createProgressReview(ticketId, payload, { signal } = {}) {
  return aiReviewRequest(`/tickets/${ticketId}/ai-reviews/progress`, payload, signal);
}

export function acceptProgressReview(ticketId, reviewId, suggestionKeys) {
  return request(`/tickets/${ticketId}/ai-reviews/progress/${reviewId}/accept`, {
    method: "POST", body: JSON.stringify({ suggestion_keys: suggestionKeys }),
  });
}

export function rejectProgressReview(ticketId, reviewId) {
  return request(`/tickets/${ticketId}/ai-reviews/progress/${reviewId}/reject`, { method: "POST" });
}

export function reviewTicketDraft(ticket, { signal } = {}) {
  return aiReviewRequest("/ai-reviews/draft", ticket, signal);
}

export function proposeWorkIntake(sourceText, { signal } = {}) {
  return request("/work-intake/proposals", {
    method: "POST",
    body: JSON.stringify({ source_text: sourceText }),
    signal,
  });
}

export function getCurrentWorkIntake() {
  return request("/work-intake/proposals/current");
}

export function getWorkIntake(attemptId) {
  return request(`/work-intake/proposals/${attemptId}`);
}

export function refineWorkIntake(attemptId, answers) {
  return request(`/work-intake/proposals/${attemptId}/refine`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function cancelWorkIntake(attemptId) {
  return request(`/work-intake/proposals/${attemptId}/cancel`, {
    method: "POST",
  });
}

export function dismissWorkIntake(attemptId) {
  return request(`/work-intake/proposals/${attemptId}/dismiss`, {
    method: "POST",
  });
}

export function acceptAIReview(ticketId, reviewId, options) {
  return request(
    `/tickets/${ticketId}/ai-reviews/${reviewId}/accept`,
    {
      method: "POST",
      body: JSON.stringify(options),
    }
  );
}

export function updateSubtask(ticketId, subtaskId, updates) {
    return request(
      `/tickets/${ticketId}/subtasks/${subtaskId}`,
      {
        method: "PATCH",
        body: JSON.stringify(updates),
      }
    );
}
  
export function deleteSubtask(ticketId, subtaskId) {
  return request(`/tickets/${ticketId}/subtasks/${subtaskId}`, {
    method: "DELETE",
  });
}

export function updateTicket(ticketId, updates) {
    return request(`/tickets/${ticketId}`, {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
}

export function saveDrawerSession(ticketId, session) {
  return request(`/tickets/${ticketId}/drawer-session`, {
    method: "PUT",
    body: JSON.stringify(session),
  });
}

export function createTicket(ticket) {
    return request("/tickets/", {
      method: "POST",
      body: JSON.stringify(ticket),
    });
}

export function createSubtask(ticketId, subtask) {
  return request(`/tickets/${ticketId}/subtasks/`, {
    method: "POST",
    body: JSON.stringify(subtask),
  });
}

export function saveSubtasks(ticketId, subtasks) {
  return request(`/tickets/${ticketId}/subtasks/`, {
    method: "PUT",
    body: JSON.stringify({ subtasks }),
  });
}


export function searchWork(query, filters = {}) {
  const params = new URLSearchParams({ q: query });
  Object.entries(filters).forEach(([name, enabled]) => {
    if (enabled) params.set(name, "true");
  });
  return request(`/search/?${params}`);
}
