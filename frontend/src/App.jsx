// Coordinates shared Telaryn data and workflows while focused components own presentation.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./App.css";
import "./components/tickets/TicketWorkflow.css";
import { readNewTicketDraft, saveNewTicketDraft, clearNewTicketDraft } from "./newTicketDraft";
import {
  hasRecentAITransmissionAcknowledgment,
  recordAITransmissionAcknowledgment,
} from "./aiTransmissionAcknowledgment";
import { readWorkspaceLocation, saveWorkspaceLocation, clearWorkspaceLocation } from "./workspaceLocation";
import AITransmissionDisclosure from "./components/AITransmissionDisclosure";
import ProjectModal from "./components/projects/ProjectModal";
import AcceptanceCriteriaSection from "./components/tickets/AcceptanceCriteriaSection";
import NewTicketModal from "./components/tickets/NewTicketModal";
import SubtasksSection from "./components/tickets/SubtasksSection";
import TicketActivitySection from "./components/tickets/TicketActivitySection";
import TicketDetailsSection, { TicketPublicReference } from "./components/tickets/TicketDetailsSection";
import TicketAIReviewSection from "./components/tickets/TicketAIReviewSection";
import TicketDrawer from "./components/tickets/TicketDrawer";
import TicketDrawerRelatedContent from "./components/tickets/TicketDrawerRelatedContent";
import TicketDrawerActions from "./components/tickets/TicketDrawerActions";
import TicketStatusSection from "./components/tickets/TicketStatusSection";
import DrawerStagedChangesDialog from "./components/tickets/DrawerStagedChangesDialog";
import TicketProgressReviewPanel from "./components/tickets/TicketProgressReviewPanel";
import { buildDrawerSessionChanges } from "./components/tickets/drawerSession";
import {
  completeRemainingCriteria,
  completeRemainingSubtasks,
} from "./components/tickets/bulkScopeCompletion";
import { requiresFinalScopeResolution } from "./components/tickets/ticketScopeResolution";
import { appendUniqueStructureItems, parseStructureList } from "./components/tickets/parseStructureList";
import useTicketActivity from "./hooks/useTicketActivity";
import useIntakeNavigation from "./hooks/useIntakeNavigation";
import useMobileViewportHeight from "./hooks/useMobileViewportHeight";
import AccessRequestReview from "./components/AccessRequestReview";
import UserManagement from "./components/UserManagement";
import FeedbackAdministration from "./components/FeedbackAdministration";
import AboutView from "./views/AboutView";
import MyWorkView from "./views/MyWorkView";
import ProjectsView from "./views/ProjectsView";
import SearchView from "./views/SearchView";
import ReportsView from "./views/ReportsView";
import SettingsView from "./views/SettingsView";
import FeedbackView from "./views/FeedbackView";
import PublicLandingView from "./views/PublicLandingView";
import PublicPolicyView from "./views/PublicPolicyView";
import GettingStartedView from "./views/GettingStartedView";
import OnboardingPanel from "./components/OnboardingPanel";
import InvitationAcceptanceView from "./views/InvitationAcceptanceView";
import LoginView from "./views/LoginView";
import { AtlasBrand } from "./components/AtlasBrand";
import { DEFAULT_MY_WORK_SECTION, MY_WORK_SECTIONS } from "./myWorkSections";

import {
  acceptAIReview,
  acceptProgressReview,
  archiveProject as archiveProjectRequest,
  cancelWorkIntake,
  classifyArchivedProject,
  createAIReview,
  createProgressReview,
  createProject,
  createTicket,
  getProjects,
  getMyWork,
  getWorkIntake,
  getAcceptanceCriteria,
  getSubtasks,
  getTickets,
  getCurrentSession,
  getCurrentWorkIntake,
  getDeploymentAdministratorAccess,
  getFeedbackReviewerAccess,
  getPreferences,
  getOnboarding,
  updateOnboarding,
  savePreferences,
  login,
  logout,
  reviewTicketDraft,
  proposeWorkIntake,
  refineWorkIntake,
  dismissWorkIntake,
  restoreProject as restoreProjectRequest,
  saveDrawerSession,
  updateMyWorkPreference,
  updateProject,
  updateProjectAIContextPolicy,
  getReportProjects,
  generateActivityReport,
  rejectProgressReview,
} from "./api";

const suggestedItemText = (item) => (typeof item === "string" ? item : item?.text || "");

function isMobileExecutionViewport() {
  return typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 800px)").matches;
}

function App({ initialLogin = false }) {
  useMobileViewportHeight();
  const [currentUser, setCurrentUser] = useState(null);
  const [activeMyWorkSection, setActiveMyWorkSection] = useState(DEFAULT_MY_WORK_SECTION);
  const [myWorkNavigationRequest, setMyWorkNavigationRequest] = useState({
    sectionId: DEFAULT_MY_WORK_SECTION,
    version: 0,
  });
  const intakeNavigation = useIntakeNavigation(currentUser);
  const [deploymentAdminAllowed, setDeploymentAdminAllowed] = useState(false);
  const [feedbackReviewerAllowed, setFeedbackReviewerAllowed] = useState(false);
  const [feedbackSourceView, setFeedbackSourceView] = useState("work");
  const mobileMoreRef = useRef(null);
  const [newTicketRecovered, setNewTicketRecovered] = useState(false);
  const [recoveryNotice, setRecoveryNotice] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [showLogin, setShowLogin] = useState(initialLogin);
  // Application-level data, project selection, and initial load state.
  const [tickets, setTickets] = useState([]);
  const [archivedTickets, setArchivedTickets] = useState([]);
  const [projects, setProjects] = useState([]);
  const [archivedProjects, setArchivedProjects] = useState([]);
  const [myWork, setMyWork] = useState(null);
  const [myWorkLoading, setMyWorkLoading] = useState(true);
  const [myWorkError, setMyWorkError] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [focusUndo, setFocusUndo] = useState(null);
  const [drawerFocusPending, setDrawerFocusPending] = useState(false);
  const [progressReviewPrompt, setProgressReviewPrompt] = useState(null);
  const [progressReview, setProgressReview] = useState(null);
  const [selectedProgressSuggestions, setSelectedProgressSuggestions] = useState([]);
  const [progressReviewLoading, setProgressReviewLoading] = useState(false);
  const [progressReviewApplying, setProgressReviewApplying] = useState(false);
  const [progressReviewError, setProgressReviewError] = useState(null);
  const [drawerFocusNotice, setDrawerFocusNotice] = useState(null);
  const [drawerFocusError, setDrawerFocusError] = useState(null);
  const [defaultProjectId, setDefaultProjectId] = useState(null);
  const [preferenceError, setPreferenceError] = useState(null);
  const [savingPreference, setSavingPreference] = useState(false);
  const [selectedProjectDetailId, setSelectedProjectDetailId] = useState(null);
  const [projectFormMode, setProjectFormMode] = useState(null);
  const [projectForm, setProjectForm] = useState({
    name: "",
    description: "",
    purpose: "",
    why_it_matters: "",
    target_date: "",
    life_context: "unclassified",
    ai_context_enabled: true,
  });
  const [projectError, setProjectError] = useState(null);
  const [savingProject, setSavingProject] = useState(false);
  const [pendingGuidedProjectTickets, setPendingGuidedProjectTickets] = useState([]);
  const [guidedTicketReviewProgress, setGuidedTicketReviewProgress] = useState(null);
  const directGuidedTicketDraft = useRef(false);
  const [guidedIntakeResetVersion, setGuidedIntakeResetVersion] = useState(0);
  const [projectArchivePending, setProjectArchivePending] = useState(false);
  const [projectArchiveError, setProjectArchiveError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // The open ticket and the detail collections that are loaded with it.
  const [selectedTicket, setSelectedTicket] = useState(null);
  const {
    items: ticketActivity,
    loading: ticketActivityLoading,
    error: ticketActivityError,
    expanded: ticketActivityExpanded,
    adding: addingTicketUpdate,
    draft: newTicketUpdate,
    saving: savingTicketUpdate,
    load: loadTicketActivity,
    refresh: refreshTicketActivity,
    reset: resetTicketActivity,
    setExpanded: setTicketActivityExpanded,
    startAdding: startAddingTicketUpdate,
    setDraft: setNewTicketUpdate,
    cancelAdding: cancelAddingTicketUpdate,
    recordUpdate: recordTicketUpdate,
  } = useTicketActivity();
  const [subtasks, setSubtasks] = useState([]);
  const [subtasksLoading, setSubtasksLoading] = useState(false);
  const [subtasksError, setSubtasksError] = useState(null);
  const [editingSubtasks, setEditingSubtasks] = useState(false);
  const [editSubtasks, setEditSubtasks] = useState([]);
  const [editingSubtaskKey, setEditingSubtaskKey] = useState(null);
  const [savingTicketEdits, setSavingTicketEdits] = useState(false);
  const [acceptanceCriteria, setAcceptanceCriteria] = useState([]);
  const [acceptanceCriteriaLoading, setAcceptanceCriteriaLoading] = useState(false);
  const [acceptanceCriteriaError, setAcceptanceCriteriaError] = useState(null);
  const [editingAcceptanceCriteria, setEditingAcceptanceCriteria] = useState(false);
  const [editAcceptanceCriteria, setEditAcceptanceCriteria] = useState([]);
  const [editingCriterionKey, setEditingCriterionKey] = useState(null);
  const [newCriterionText, setNewCriterionText] = useState("");
  const [stagedCommitSection, setStagedCommitSection] = useState(null);
  const [closeAfterCommit, setCloseAfterCommit] = useState(false);
  const [progressSessionActive, setProgressSessionActive] = useState(false);
  const [drawerSessionNote, setDrawerSessionNote] = useState("");
  const [scopeResolutionChoice, setScopeResolutionChoice] = useState(null);
  const [drawerRelatedState, setDrawerRelatedState] = useState("idle");
  const drawerRequestVersion = useRef(0);

  // Existing-ticket AI review is always advisory until the user applies choices.
  const [aiReview, setAIReview] = useState(null);
  const [aiReviewLoading, setAIReviewLoading] = useState(false);
  const [aiReviewError, setAIReviewError] = useState(null);
  const [applyingReview, setApplyingReview] = useState(false);
  const aiReviewRequestRunning = useRef(false);
  const aiReviewAbortController = useRef(null);
  const applyReviewRequestRunning = useRef(false);
  const [pendingAITransmission, setPendingAITransmission] = useState(null);

  function requestAITransmission(action) {
    if (hasRecentAITransmissionAcknowledgment()) {
      action();
      return;
    }
    setPendingAITransmission(() => action);
  }

  function cancelAITransmission() {
    setPendingAITransmission(null);
  }

  function continueAITransmission() {
    const action = pendingAITransmission;
    recordAITransmissionAcknowledgment();
    setPendingAITransmission(null);
    action?.();
  }

  // App preferences and the current review selections stay local to the UI.
  const [mobileExecutionMode, setMobileExecutionMode] = useState(
    isMobileExecutionViewport
  );
  const [activeView, setActiveView] = useState(() =>
    "work"
  );
  const [publicPage, setPublicPage] = useState(() => {
    if (window.location.hash === "#/getting-started") return "getting-started";
    if (window.location.hash === "#/privacy") return "privacy";
    if (window.location.hash === "#/terms") return "terms";
    return "about";
  });
  const [projectsNavigationVersion, setProjectsNavigationVersion] = useState(0);
  const [theme, setTheme] = useState(
    () => window.localStorage.getItem("atlas-theme") || "dark"
  );

  function navigateToMyWorkSection(sectionId) {
    setActiveView("work");
    setActiveMyWorkSection(sectionId);
    setMyWorkNavigationRequest((current) => ({
      sectionId,
      version: current.version + 1,
    }));
  }

  function openProjectsView() {
    setProjectsNavigationVersion((version) => version + 1);
    setActiveView("projects");
  }

  function openFeedbackView() {
    if (activeView !== "feedback") setFeedbackSourceView(activeView);
    setActiveView("feedback");
  }

  function closeFeedbackView() {
    setActiveView(feedbackSourceView === "feedback" ? "work" : feedbackSourceView);
  }

  useEffect(() => {
    function readPublicPage() {
      if (window.location.hash === "#/getting-started") setPublicPage("getting-started");
      else if (window.location.hash === "#/privacy") setPublicPage("privacy");
      else if (window.location.hash === "#/terms") setPublicPage("terms");
      else setPublicPage("about");
    }
    window.addEventListener("hashchange", readPublicPage);
    return () => window.removeEventListener("hashchange", readPublicPage);
  }, []);

  useEffect(() => {
    if (currentUser) return;
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [currentUser, publicPage]);

  const refreshOnboarding = useCallback(() => {
    if (!currentUser) return Promise.resolve(null);
    return getOnboarding().then((value) => {
      setOnboarding(value);
      return value;
    });
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser) return;
    refreshOnboarding().catch(() => {});
  }, [currentUser, tickets.length, myWork?.current_focus?.id, refreshOnboarding]);

  function runOnboardingAction(key) {
    if (key === "shape") { setActiveView("getting-started"); return; }
    if (key === "focus") { navigateToMyWorkSection("suggested-next"); return; }
    if (key === "record" && myWork?.current_focus) {
      const ticket = tickets.find((item) => item.id === myWork.current_focus.id);
      if (ticket) openTicket(ticket);
      return;
    }
    navigateToMyWorkSection("capture-work");
  }

  async function setOnboardingDismissed(dismissed) {
    setOnboarding(await updateOnboarding(dismissed));
    if (!dismissed) navigateToMyWorkSection("current-focus");
  }

  function openSearchResult(result) {
    if (result.resource_type === "project") {
      setSelectedProjectDetailId(result.project_id);
      setActiveView("projects");
      return;
    }

    const ticket = [...tickets, ...archivedTickets].find(
      (item) => item.id === result.ticket_id
    );
    if (ticket) openTicket(ticket);
  }

  const [reviewOptions, setReviewOptions] = useState({
    apply_title: true,
    apply_description: true,
    apply_priority: true,
    apply_ticket_type: true,
    create_subtasks: true,
  });
  const [selectedReviewCriteria, setSelectedReviewCriteria] = useState([]);

  // Separate workflows prevent competing edits from sharing a single save state.
  const [editingTicket, setEditingTicket] = useState(false);
  const [editTicketError, setEditTicketError] = useState(null);
  const [changingStatus, setChangingStatus] = useState(false);
  const [statusChangeError, setStatusChangeError] = useState(null);
  const [statusForm, setStatusForm] = useState({
    status: "ready",
    status_note: "",
  });

  const [editForm, setEditForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    ticket_type: "task",
    project_id: null,
    ai_context_enabled: true,
  });

  // New-ticket drafting keeps human input separate from optional AI proposals.
  const [creatingTicket, setCreatingTicket] = useState(false);
  const [savingNewTicket, setSavingNewTicket] = useState(false);
  const [newTicketError, setNewTicketError] = useState(null);
  const [draftReview, setDraftReview] = useState(null);
  const [draftReviewLoading, setDraftReviewLoading] = useState(false);
  const draftReviewAbortController = useRef(null);
  const [draftReviewOptions, setDraftReviewOptions] = useState({
    apply_title: true,
    apply_description: true,
    apply_priority: true,
    apply_ticket_type: true,
  });
  const [selectedDraftSubtasks, setSelectedDraftSubtasks] = useState([]);
  const [selectedDraftCriteria, setSelectedDraftCriteria] = useState([]);
  const [selectedDraftSubtaskRevisions, setSelectedDraftSubtaskRevisions] =
    useState([]);
  const [selectedDraftCriterionRevisions, setSelectedDraftCriterionRevisions] =
    useState([]);
  const [newTicketSubtasks, setNewTicketSubtasks] = useState([]);
  const [newTicketCriteria, setNewTicketCriteria] = useState([]);
  const [newSubtaskInput, setNewSubtaskInput] = useState("");
  const [newCriterionInput, setNewCriterionInput] = useState("");

  const [newTicketForm, setNewTicketForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    ticket_type: "task",
    project_id: null,
    ai_context_enabled: true,
  });

  useEffect(() => {
    function clearExpiredSession() {
      setCurrentUser(null);
      setShowLogin(false);
      setLoading(true);
    }
    window.addEventListener("atlas:unauthorized", clearExpiredSession);
    return () => window.removeEventListener("atlas:unauthorized", clearExpiredSession);
  }, []);

  useEffect(() => {
    getCurrentSession()
      .then(setCurrentUser)
      .catch((err) => {
        if (err.status !== 401) setAuthError(err.message);
      })
      .finally(() => setAuthChecking(false));
  }, []);

  // Load workspace data only after the server has established request identity.
  useEffect(() => {
    if (!currentUser) return;
    async function loadAtlas() {
      setSelectedTicket(null);
      setCreatingTicket(false);
      setNewTicketRecovered(false);
      setRecoveryNotice(null);
      try {
        const [ticketData, projectData, preferences] = await Promise.all([
          getTickets(true),
          getProjects(true),
          getPreferences(),
        ]);
        const activeProjects = projectData.filter((project) => !project.archived_at);
        const preservedProjects = projectData.filter((project) => project.archived_at);
        const archivedProjectIds = new Set(preservedProjects.map((project) => project.id));
        const activeTickets = ticketData.filter(
          (ticket) => ticket.project_id === null || !archivedProjectIds.has(ticket.project_id),
        );
        const preservedTickets = ticketData.filter(
          (ticket) => archivedProjectIds.has(ticket.project_id),
        );

        setDefaultProjectId(preferences.default_project_id);
        setPreferenceError(null);
        setTickets(activeTickets);
        setArchivedTickets(preservedTickets);
        setProjects(activeProjects);
        setArchivedProjects(preservedProjects);
        const draft = readNewTicketDraft(currentUser);
        const location = readWorkspaceLocation(currentUser);
        if (location) {
          setActiveView(location.view === "dashboard" ? "work" : location.view);
          if (projectData.some((project) => project.id === location.projectId)) {
            setSelectedProjectDetailId(location.projectId);
          }
          const ticket = ticketData.find((item) => item.id === location.ticketId);
          if (ticket && !draft) {
            await openTicket(ticket);
            if (location.interruptedEdits) {
              setRecoveryNotice("Your ticket was reopened using saved data. Unsaved edits from before the reload were not recovered.");
            }
          }
        }
        if (draft) {
          setNewTicketForm({ ...draft.form, project_id: activeProjects.some(p => p.id === draft.form.project_id) ? draft.form.project_id : null });
          setNewTicketCriteria(draft.criteria);
          setNewTicketSubtasks(draft.subtasks);
          setNewCriterionInput(typeof draft.criterionInput === "string" ? draft.criterionInput : "");
          setNewSubtaskInput(typeof draft.subtaskInput === "string" ? draft.subtaskInput : "");
          setDraftReview(null);
          setNewTicketRecovered(true);
          setCreatingTicket(true);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    loadAtlas();
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser) return undefined;
    let active = true;
    getDeploymentAdministratorAccess()
      .then(result => { if (active) setDeploymentAdminAllowed(Boolean(result.allowed)); })
      .catch(() => { if (active) setDeploymentAdminAllowed(false); });
    return () => { active = false; };
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser) return undefined;
    let active = true;
    getFeedbackReviewerAccess()
      .then(result => { if (active) setFeedbackReviewerAllowed(Boolean(result.allowed)); })
      .catch(() => { if (active) setFeedbackReviewerAllowed(false); });
    return () => { active = false; };
  }, [currentUser]);

  // My Work is computed server-side so its ordering and workspace boundary
  // remain consistent across desktop, future mobile clients, and direct API use.
  useEffect(() => {
    // Projects also consumes Current Focus identity, so refresh
    // the same server-owned state before presenting filtered ticket results.
    if (!currentUser || !["work", "projects"].includes(activeView)) return;
    let active = true;
    getMyWork()
      .then((data) => {
        if (active) {
          setMyWork(data);
          setMyWorkError(null);
        }
      })
      .catch((err) => {
        if (active) setMyWorkError(err.message);
      })
      .finally(() => {
        if (active) setMyWorkLoading(false);
      });
    return () => {
      active = false;
    };
  }, [activeView, currentUser, tickets]);

  async function submitLogin(email, password) {
    setAuthSubmitting(true);
    setAuthError(null);
    try {
      setLoading(true);
      setActiveView("work");
      const user = await login(email, password);
      clearWorkspaceLocation(user);
      setCurrentUser(user);
    } catch (err) {
      setAuthError(err.message);
      setLoading(false);
    } finally {
      setAuthSubmitting(false);
    }
  }

  async function endSession() {
    if (drawerHasUnsavedWork && !window.confirm("Sign out and discard unsaved drawer changes?")) return;
    try {
      await logout();
    } finally {
      clearWorkspaceLocation(currentUser);
      clearNewTicketDraft(currentUser);
      setCreatingTicket(false);
      closeTicket();
      setRecoveryNotice(null);
      setCurrentUser(null);
      setShowLogin(false);
      setTickets([]);
      setArchivedTickets([]);
      setProjects([]);
      setArchivedProjects([]);
      setLoading(true);
    }
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("atlas-theme", theme);
  }, [theme]);

  // Track responsive presentation without changing the user's selected view.
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return undefined;
    }

    const query = window.matchMedia("(max-width: 800px)");
    function updateMobileExecutionMode(event) {
      setMobileExecutionMode(event.matches);
    }

    updateMobileExecutionMode(query);
    query.addEventListener?.("change", updateMobileExecutionMode);
    return () => query.removeEventListener?.("change", updateMobileExecutionMode);
  }, []);

  const effectiveDefaultProjectId = projects.some(p => p.id === defaultProjectId)
    ? defaultProjectId : null;

  async function changeDefaultProject(projectId) {
    if (savingPreference) return;
    setSavingPreference(true);
    setPreferenceError(null);
    try {
      const saved = await savePreferences(projectId);
      setDefaultProjectId(saved.default_project_id);
      try {
        window.localStorage.removeItem("atlas-current-project-id");
        window.localStorage.removeItem("atlas-default-project-id");
      } catch { /* The server save succeeded even if local cleanup is unavailable. */ }
    } catch (err) {
      setPreferenceError(err.message);
    } finally {
      setSavingPreference(false);
    }
  }

  useEffect(() => {
    if (!currentUser || loading || savingPreference) return undefined;
    let active = true;
    function refreshDefault() {
      if (document.visibilityState === "hidden") return;
      getPreferences().then(saved => {
        if (active) setDefaultProjectId(saved.default_project_id);
      }).catch(() => { /* Keep the last confirmed preference while offline. */ });
    }
    window.addEventListener("focus", refreshDefault);
    document.addEventListener("visibilitychange", refreshDefault);
    return () => {
      active = false;
      window.removeEventListener("focus", refreshDefault);
      document.removeEventListener("visibilitychange", refreshDefault);
    };
  }, [currentUser, loading, savingPreference]);

  // Derived workflow rules keep UI affordances aligned with backend validation.
  const allProjects = [...projects, ...archivedProjects];
  const selectedProject = allProjects.find(
    (project) => project.id === selectedProjectDetailId
  );
  const selectedTicketArchived = Boolean(
    selectedTicket && archivedProjects.some(
      (project) => project.id === selectedTicket.project_id
    )
  );
  const statusChanged = Boolean(
    selectedTicket && statusForm.status !== selectedTicket.status
  );
  const visibleCriteriaDraft = progressSessionActive || editingTicket
    ? editAcceptanceCriteria
    : acceptanceCriteria;
  const visibleSubtasksDraft = progressSessionActive || editingTicket
    ? editSubtasks
    : subtasks;
  const hasIncompleteTicketStructure =
    visibleCriteriaDraft.some(
      (criterion) => !criterion.completed && !criterion.deferred
    ) ||
    visibleSubtasksDraft.some(
      (subtask) => !["done", "cancelled", "deferred"].includes(subtask.status)
    );
  const statusNoteRequired =
    statusChanged &&
    (["blocked", "cancelled"].includes(statusForm.status) ||
      (statusForm.status === "done" && hasIncompleteTicketStructure));
  const canStartTicketEditing =
    selectedTicket &&
    drawerRelatedState === "ready" &&
    !ticketActivityError &&
    !acceptanceCriteriaError &&
    !subtasksError &&
    !selectedTicketArchived &&
    !editingTicket &&
    !editingAcceptanceCriteria &&
    !editingSubtasks &&
    !changingStatus &&
    !addingTicketUpdate &&
    !aiReview &&
    !aiReviewLoading;
  const drawerSessionChanges = useMemo(
    () => (editingTicket || progressSessionActive) && selectedTicket
      ? buildDrawerSessionChanges({
          ticket: selectedTicket,
          ticketDraft: { ...editForm, status: statusForm.status },
          criteria: acceptanceCriteria,
          criteriaDraft: editAcceptanceCriteria,
          subtasks,
          subtasksDraft: editSubtasks,
          projects,
        })
      : [],
    [
      acceptanceCriteria,
      editAcceptanceCriteria,
      editForm,
      editSubtasks,
      editingTicket,
      progressSessionActive,
      projects,
      selectedTicket,
      statusForm.status,
      subtasks,
    ],
  );
  const drawerHasUnsavedWork = Boolean(selectedTicket && (
    drawerSessionChanges.length || editingTicket || editingAcceptanceCriteria ||
    editingSubtasks || changingStatus || addingTicketUpdate || drawerSessionNote
  ));

  useEffect(() => {
    if (!currentUser || loading) return;
    saveWorkspaceLocation(currentUser, {
      view: activeView,
      ticketId: selectedTicket?.id,
      projectId: selectedProjectDetailId,
      interruptedEdits: drawerHasUnsavedWork,
    });
  }, [currentUser, loading, activeView, selectedTicket?.id, selectedProjectDetailId, drawerHasUnsavedWork]);

  useEffect(() => {
    if (!drawerHasUnsavedWork) return undefined;
    function warnBeforeUnload(event) {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [drawerHasUnsavedWork]);

  useEffect(() => {
    if (!currentUser || loading) return;
    if (!creatingTicket) {
      clearNewTicketDraft(currentUser);
      return;
    }
    saveNewTicketDraft(currentUser, {
      form: newTicketForm, criteria: newTicketCriteria, subtasks: newTicketSubtasks,
      criterionInput: newCriterionInput, subtaskInput: newSubtaskInput,
    });
  }, [currentUser, loading, creatingTicket, newTicketForm, newTicketCriteria, newTicketSubtasks, newCriterionInput, newSubtaskInput]);

  useEffect(() => {
    function dismissAccount(event) {
      const menu = mobileMoreRef.current;
      if (!menu?.open) return;
      if (event.type === "keydown") {
        if (event.key !== "Escape") return;
        menu.open = false;
        menu.querySelector("summary")?.focus();
      } else if (!menu.contains(event.target)) {
        menu.open = false;
      }
    }
    document.addEventListener("pointerdown", dismissAccount);
    document.addEventListener("focusin", dismissAccount);
    document.addEventListener("keydown", dismissAccount);
    return () => {
      document.removeEventListener("pointerdown", dismissAccount);
      document.removeEventListener("focusin", dismissAccount);
      document.removeEventListener("keydown", dismissAccount);
    };
  }, []);

  const progressNoteRequired = progressSessionActive && (
    acceptanceCriteria.some((original) => {
      const draft = editAcceptanceCriteria.find((item) => item.id === original.id);
      return original.completed && draft && !draft.completed;
    }) ||
    subtasks.some((original) => {
      const draft = editSubtasks.find((item) => item.id === original.id);
      return original.status === "done" && draft && draft.status !== "done";
    })
  );
  const scopeNoteRequired = drawerSessionChanges.some(
    (change) =>
      change.kind === "removed" ||
      change.label.includes("Deferred") ||
      change.label.includes("Restored")
  );
  const drawerNoteRequired = progressNoteRequired || statusNoteRequired || scopeNoteRequired;
  const finalScopeResolutionRequired = useMemo(
    () => Boolean(
      (editingTicket || progressSessionActive) &&
      selectedTicket &&
      requiresFinalScopeResolution({
        criteria: acceptanceCriteria,
        criteriaDraft: editAcceptanceCriteria,
        subtasks,
        subtasksDraft: editSubtasks,
      })
    ),
    [
      acceptanceCriteria,
      editAcceptanceCriteria,
      editSubtasks,
      editingTicket,
      progressSessionActive,
      selectedTicket,
      subtasks,
    ],
  );
  const currentTicketStatusLabel = selectedTicket
    ? selectedTicket.status
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    : "";
  const selectedTicketWorkItem = useMemo(() => {
    if (!selectedTicket || !myWork) return null;
    const sections = [
      myWork.current_focus,
      ...(myWork.suggestions || []),
      ...(myWork.upcoming || []),
      ...(myWork.focus_now || []),
      ...(myWork.needs_attention || []),
      ...(myWork.up_next || []),
      ...(myWork.in_review || []),
      ...(myWork.recently_completed || []),
    ].filter(Boolean);
    return sections.find((item) => item.id === selectedTicket.id) || null;
  }, [myWork, selectedTicket]);
  const selectedTicketFocusState = useMemo(() => {
    if (selectedTicketArchived || !selectedTicket || !["ready", "in_progress"].includes(selectedTicket.status)) {
      return "ineligible";
    }
    if (myWork?.current_focus?.id === selectedTicket.id) return "current";
    return selectedTicketWorkItem?.availability_mode &&
      selectedTicketWorkItem.availability_mode !== "available"
      ? "unavailable"
      : "available";
  }, [myWork, selectedTicket, selectedTicketArchived, selectedTicketWorkItem]);

  async function saveMyWorkPreference(ticketId, preference) {
    setMyWorkLoading(true);
    setMyWorkError(null);
    try {
      const updated = await updateMyWorkPreference(ticketId, preference);
      setMyWork(updated);
      return updated;
    } catch (err) {
      setMyWorkError(err.message);
      return null;
    } finally {
      setMyWorkLoading(false);
    }
  }

  async function setCurrentFocus(workItem) {
    const previousId = myWork?.current_focus?.id || null;
    const updated = await saveMyWorkPreference(workItem.id, {
      current_focus: true,
    });
    if (updated) setFocusUndo({ previousId, currentId: workItem.id, source: "work" });
  }

  async function undoCurrentFocus() {
    if (!focusUndo) return;
    const { previousId, currentId } = focusUndo;
    const updated = previousId
      ? await saveMyWorkPreference(previousId, { current_focus: true })
      : await saveMyWorkPreference(currentId, { current_focus: false });
    if (updated) setFocusUndo(null);
  }

  async function focusSelectedTicket(makeAvailable = false) {
    if (!selectedTicket || drawerFocusPending) return;
    const previousId = myWork?.current_focus?.id || null;
    setDrawerFocusPending(true);
    setDrawerFocusNotice(null);
    setDrawerFocusError(null);
    try {
      const updated = await updateMyWorkPreference(selectedTicket.id, {
        current_focus: true,
        make_available_and_focus: makeAvailable,
      });
      setMyWork(updated);
      setFocusUndo({ previousId, currentId: selectedTicket.id, source: "drawer" });
      setDrawerFocusNotice("Current Focus updated.");
    } catch (err) {
      setDrawerFocusError(err.message);
    } finally {
      setDrawerFocusPending(false);
    }
  }

  async function undoDrawerFocus() {
    if (!focusUndo || drawerFocusPending) return;
    const { previousId, currentId } = focusUndo;
    setDrawerFocusPending(true);
    setDrawerFocusNotice(null);
    setDrawerFocusError(null);
    try {
      const updated = previousId
        ? await updateMyWorkPreference(previousId, { current_focus: true })
        : await updateMyWorkPreference(currentId, { current_focus: false });
      setMyWork(updated);
      setFocusUndo(null);
      setDrawerFocusNotice(
        previousId ? "Previous Current Focus restored." : "Current Focus cleared.",
      );
    } catch (err) {
      setDrawerFocusError(err.message);
    } finally {
      setDrawerFocusPending(false);
    }
  }

  async function setWorkAvailability(workItem, availabilityMode, availableOn) {
    const updated = await saveMyWorkPreference(workItem.id, {
      availability_mode: availabilityMode,
      available_on: availableOn,
    });
    if (updated) setFocusUndo(null);
  }

  // Project actions.
  function getProjectName(projectId) {
    if (!projectId) {
      return "No project";
    }

    const project = allProjects.find(
      (item) => item.id === projectId
    );

    return project ? project.name : "Unknown project";
  }

  function openNewProject() {
    setPendingGuidedProjectTickets([]);
    setGuidedTicketReviewProgress(null);
    setProjectForm({
      name: "",
      description: "",
      purpose: "",
      why_it_matters: "",
      target_date: "",
      life_context: "unclassified",
      ai_context_enabled: true,
    });
    setProjectError(null);
    setProjectFormMode("create");
  }

  function openProjectEditor() {
    if (!selectedProject || selectedProject.archived_at) {
      return;
    }

    setProjectForm({
      name: selectedProject.name,
      description: selectedProject.description || "",
      purpose: selectedProject.purpose || "",
      why_it_matters: selectedProject.why_it_matters || "",
      target_date: selectedProject.target_date || "",
      life_context: selectedProject.life_context || "unclassified",
      ai_context_enabled: selectedProject.ai_context_enabled !== false,
    });
    setProjectError(null);
    setProjectFormMode("edit");
  }

  function closeProjectForm() {
    setProjectFormMode(null);
    setProjectError(null);
  }

  function cancelProjectForm() {
    setPendingGuidedProjectTickets([]);
    setGuidedTicketReviewProgress(null);
    closeProjectForm();
  }

  async function saveProject(event) {
    event.preventDefault();
    const payload = {
      name: projectForm.name.trim(),
      description: projectForm.description.trim() || null,
      purpose: projectForm.purpose.trim() || null,
      why_it_matters: projectForm.why_it_matters.trim() || null,
      target_date: projectForm.target_date || null,
      life_context: projectForm.life_context,
    };

    if (!payload.name) {
      setProjectError("A project name is required.");
      return;
    }

    setSavingProject(true);
    setProjectError(null);

    try {
      if (projectFormMode === "edit" && selectedProject) {
        let updated = await updateProject(selectedProject.id, payload);
        if (updated.ai_context_enabled !== projectForm.ai_context_enabled) {
          updated = await updateProjectAIContextPolicy(
            selectedProject.id,
            projectForm.ai_context_enabled,
          );
        }
        setProjects((current) =>
          current.map((project) =>
            project.id === updated.id ? updated : project
          )
        );
      } else {
        const created = await createProject({
          ...payload,
          ...(projectForm.ai_context_enabled === false
            ? { ai_context_enabled: false }
            : {}),
        });
        setProjects((current) => [created, ...current]);
        setSelectedProjectDetailId(created.id);
        if (pendingGuidedProjectTickets.length) {
          const [firstTicket, ...remainingTickets] = pendingGuidedProjectTickets.map(
            (ticket) => ({ ...ticket, project_id: created.id })
          );
          setPendingGuidedProjectTickets(remainingTickets);
          setGuidedTicketReviewProgress({
            current: 1,
            total: pendingGuidedProjectTickets.length,
            projectId: created.id,
          });
          closeProjectForm();
          openGuidedTicketDraft(firstTicket);
          return;
        }
      }

      closeProjectForm();
    } catch (err) {
      setProjectError(err.message);
    } finally {
      setSavingProject(false);
    }
  }

  async function archiveSelectedProject(project, archiveData) {
    if (!project || projectArchivePending) return null;
    setProjectArchivePending(true);
    setProjectArchiveError(null);
    try {
      const archived = await archiveProjectRequest(project.id, archiveData);
      const movedTickets = tickets.filter((ticket) => ticket.project_id === project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
      setArchivedProjects((current) => [archived, ...current.filter((item) => item.id !== project.id)]);
      setTickets((current) => current.filter((ticket) => ticket.project_id !== project.id));
      setArchivedTickets((current) => [
        ...movedTickets,
        ...current.filter((ticket) => ticket.project_id !== project.id),
      ]);
      if (defaultProjectId === project.id) setDefaultProjectId(null);
      setFocusUndo(null);
      setMyWork(await getMyWork());
      return archived;
    } catch (err) {
      setProjectArchiveError(err.message);
      return null;
    } finally {
      setProjectArchivePending(false);
    }
  }

  async function classifySelectedArchivedProject(project, archiveData) {
    if (!project || projectArchivePending) return null;
    setProjectArchivePending(true);
    setProjectArchiveError(null);
    try {
      const classified = await classifyArchivedProject(project.id, archiveData);
      setArchivedProjects((current) => current.map((item) =>
        item.id === project.id ? classified : item
      ));
      return classified;
    } catch (err) {
      setProjectArchiveError(err.message);
      return null;
    } finally {
      setProjectArchivePending(false);
    }
  }

  async function restoreSelectedProject(project) {
    if (!project || projectArchivePending) return null;
    setProjectArchivePending(true);
    setProjectArchiveError(null);
    try {
      const restored = await restoreProjectRequest(project.id);
      const movedTickets = archivedTickets.filter((ticket) => ticket.project_id === project.id);
      setArchivedProjects((current) => current.filter((item) => item.id !== project.id));
      setProjects((current) => [restored, ...current.filter((item) => item.id !== project.id)]);
      setArchivedTickets((current) => current.filter((ticket) => ticket.project_id !== project.id));
      setTickets((current) => [
        ...movedTickets,
        ...current.filter((ticket) => ticket.project_id !== project.id),
      ]);
      return restored;
    } catch (err) {
      setProjectArchiveError(err.message);
      return null;
    } finally {
      setProjectArchivePending(false);
    }
  }

  // Ticket details and structure editing actions.
  function initializeDrawerDrafts(
    progressChange = null,
    ticketSource = selectedTicket,
    criteriaSource = acceptanceCriteria,
    subtasksSource = subtasks,
  ) {
    if (!ticketSource) return;

    setEditForm({
      title: ticketSource.title,
      description: ticketSource.description || "",
      priority: ticketSource.priority,
      ticket_type: ticketSource.ticket_type,
      project_id: ticketSource.project_id,
      ai_context_enabled: ticketSource.ai_context_enabled !== false,
    });
    setEditTicketError(null);
    setStatusForm({ status: ticketSource.status, status_note: "" });
    setEditAcceptanceCriteria(criteriaSource.map((criterion) => ({
      ...criterion,
      completed: criterion.id === progressChange?.deferCriterionId
        ? false
        : criterion.id === progressChange?.criterionId
          ? !criterion.completed
          : criterion.completed,
      deferred: criterion.id === progressChange?.deferCriterionId
        ? !criterion.deferred
        : criterion.deferred,
      clientKey: `existing-${criterion.id}`,
    })));
    setEditSubtasks(subtasksSource.map((subtask) => ({
      ...subtask,
      status: subtask.id === progressChange?.subtaskId
        ? (subtask.status === "done" ? "todo" : "done")
        : subtask.id === progressChange?.deferSubtaskId
          ? (subtask.status === "deferred" ? "todo" : "deferred")
        : subtask.status,
      clientKey: `existing-${subtask.id}`,
    })));
    setEditingCriterionKey(null);
    setEditingSubtaskKey(null);
    setNewCriterionText("");
    setAcceptanceCriteriaError(null);
  }

  function startEditingTicket() {
    if (!selectedTicket || acceptanceCriteriaLoading || subtasksLoading) return;
    if (!progressSessionActive) initializeDrawerDrafts();
    setEditingTicket(true);
    setEditingAcceptanceCriteria(true);
    setEditingSubtasks(true);
  }

  function cancelEditingTicket() {
    setEditTicketError(null);
    setEditingTicket(false);
    setEditingAcceptanceCriteria(false);
    setEditingSubtasks(false);
    setEditAcceptanceCriteria([]);
    setEditSubtasks([]);
    setEditingCriterionKey(null);
    setEditingSubtaskKey(null);
    setNewCriterionText("");
    setStagedCommitSection(null);
    setCloseAfterCommit(false);
    setProgressSessionActive(false);
    setDrawerSessionNote("");
    setScopeResolutionChoice(null);
    setChangingStatus(false);
    setStatusForm({ status: selectedTicket.status, status_note: "" });
  }

  function undoAllDrawerChanges() {
    setEditForm({
      title: selectedTicket.title,
      description: selectedTicket.description || "",
      priority: selectedTicket.priority,
      ticket_type: selectedTicket.ticket_type,
      project_id: selectedTicket.project_id,
      ai_context_enabled: selectedTicket.ai_context_enabled !== false,
    });
    setEditAcceptanceCriteria(acceptanceCriteria.map((criterion) => ({ ...criterion, clientKey: `existing-${criterion.id}` })));
    setEditSubtasks(subtasks.map((subtask) => ({ ...subtask, clientKey: `existing-${subtask.id}` })));
    setStatusForm({ status: selectedTicket.status, status_note: "" });
    setScopeResolutionChoice(null);
    setEditingCriterionKey(null);
    setEditingSubtaskKey(null);
    setStagedCommitSection(null);
    if (!editingTicket) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
  }

  function hasStagedStructureChanges(
    criteriaDraft = editAcceptanceCriteria,
    subtasksDraft = editSubtasks,
  ) {
    return (
      criteriaDraft.length !== acceptanceCriteria.length ||
      subtasksDraft.length !== subtasks.length ||
      criteriaDraft.some((draft, index) => {
        const saved = acceptanceCriteria[index];
        return !saved || saved.id !== draft.id || saved.text !== draft.text.trim() ||
          saved.completed !== draft.completed || saved.deferred !== draft.deferred;
      }) ||
      subtasksDraft.some((draft, index) => {
        const saved = subtasks[index];
        return !saved || saved.id !== draft.id || saved.title !== draft.title.trim() ||
          (saved.description || null) !== (draft.description?.trim() || null) || saved.status !== draft.status;
      })
    );
  }

  function undoDrawerChange(key) {
    const [scope, action, identifier] = key.split(":");
    if (scope === "ticket") {
      const field = action;
      if (field === "status") {
        setStatusForm({ status: selectedTicket.status, status_note: "" });
        setScopeResolutionChoice(null);
      } else {
        setEditForm((current) => ({ ...current, [field]: field === "description" ? selectedTicket[field] || "" : selectedTicket[field] }));
      }
    } else if (scope === "criterion") {
      if (action === "added") setEditAcceptanceCriteria((current) => current.filter((item) => item.clientKey !== identifier));
      else {
        const id = Number(identifier);
        const original = acceptanceCriteria.find((item) => item.id === id);
        setEditAcceptanceCriteria((current) => {
          const without = current.filter((item) => item.id !== id);
          return acceptanceCriteria.flatMap((item) => item.id === id ? [{ ...original, clientKey: `existing-${id}` }] : without.filter((draft) => draft.id === item.id)).concat(without.filter((item) => !item.id));
        });
      }
    } else if (scope === "subtask") {
      if (action === "added") setEditSubtasks((current) => current.filter((item) => item.clientKey !== identifier));
      else {
        const id = Number(identifier);
        const original = subtasks.find((item) => item.id === id);
        setEditSubtasks((current) => {
          const without = current.filter((item) => item.id !== id);
          return subtasks.flatMap((item) => item.id === id ? [{ ...original, clientKey: `existing-${id}` }] : without.filter((draft) => draft.id === item.id)).concat(without.filter((item) => !item.id));
        });
      }
    }
    setStagedCommitSection((current) => current);
  }

  function updateTicketEditField(field, value) {
    setEditForm((current) => ({ ...current, [field]: value }));
  }

  function startEditingAcceptanceCriteria() {
    if (!selectedTicket || acceptanceCriteriaLoading) {
      return;
    }

    setEditAcceptanceCriteria(
      acceptanceCriteria.map((criterion) => ({
        ...criterion,
        clientKey: `existing-${criterion.id}`,
      }))
    );
    setEditingCriterionKey(null);
    setNewCriterionText("");
    setAcceptanceCriteriaError(null);
    setEditingAcceptanceCriteria(true);
  }

  function startEditingSubtasks() {
    if (!selectedTicket || subtasksLoading) {
      return;
    }

    setEditSubtasks(
      subtasks.map((subtask) => ({
        ...subtask,
        clientKey: `existing-${subtask.id}`,
      }))
    );
    setEditingSubtaskKey(null);
    setEditTicketError(null);
    setEditingSubtasks(true);
  }

  function addEditAcceptanceCriterion(event) {
    event.preventDefault();
    const criteria = appendUniqueStructureItems(
      editAcceptanceCriteria,
      parseStructureList(newCriterionText),
      (criterion) => criterion.text,
    );
    if (!criteria.length) return;
    setEditAcceptanceCriteria((current) => [
      ...current,
      ...criteria.map((text) => ({
        clientKey: `new-${crypto.randomUUID()}`,
        text,
        completed: false,
        deferred: false,
      })),
    ]);
    setEditingCriterionKey(null);
    setNewCriterionText("");
    setEditTicketError(null);
  }

  function updateEditAcceptanceCriterion(clientKey, text) {
    setEditAcceptanceCriteria((current) =>
      current.map((criterion) =>
        criterion.clientKey === clientKey
          ? { ...criterion, text }
          : criterion
      )
    );
  }

  function removeEditAcceptanceCriterion(clientKey) {
    setEditAcceptanceCriteria((current) =>
      current.filter((criterion) => criterion.clientKey !== clientKey)
    );
  }

  function beginEditAcceptanceCriterion(clientKey) {
    setEditingCriterionKey(clientKey);
    setAcceptanceCriteriaError(null);
  }

  function saveEditAcceptanceCriterion(clientKey) {
    const criterion = editAcceptanceCriteria.find(
      (item) => item.clientKey === clientKey
    );

    if (!criterion?.text.trim()) {
      setAcceptanceCriteriaError("Every acceptance criterion needs text.");
      return;
    }

    setAcceptanceCriteriaError(null);
    setEditingCriterionKey(null);
  }

  function cancelEditAcceptanceCriterion(clientKey) {
    const draft = editAcceptanceCriteria.find(
      (item) => item.clientKey === clientKey
    );

    if (!draft?.id) {
      removeEditAcceptanceCriterion(clientKey);
      setEditingCriterionKey(null);
      return;
    }

    const original = acceptanceCriteria.find(
      (criterion) => criterion.id === draft.id
    );
    if (original) {
      setEditAcceptanceCriteria((current) =>
        current.map((criterion) =>
          criterion.clientKey === clientKey
            ? { ...original, clientKey }
            : criterion
        )
      );
    }
    setEditingCriterionKey(null);
    setAcceptanceCriteriaError(null);
  }

  function addEditSubtask() {
    const clientKey = `new-${crypto.randomUUID()}`;
    setEditSubtasks((current) => [
      ...current,
      {
        clientKey,
        title: "",
        description: "",
        status: "todo",
      },
    ]);
    setEditingSubtaskKey(clientKey);
    setEditTicketError(null);
  }

  function updateEditSubtask(clientKey, field, value) {
    setEditSubtasks((current) =>
      current.map((subtask) =>
        subtask.clientKey === clientKey
          ? { ...subtask, [field]: value }
          : subtask
      )
    );
  }

  function removeEditSubtask(clientKey) {
    setEditSubtasks((current) =>
      current.filter((subtask) => subtask.clientKey !== clientKey)
    );
    if (editingSubtaskKey === clientKey) {
      setEditingSubtaskKey(null);
    }
  }

  function beginEditSubtask(clientKey) {
    setEditingSubtaskKey(clientKey);
    setEditTicketError(null);
  }

  function saveEditSubtask(clientKey) {
    const subtask = editSubtasks.find((item) => item.clientKey === clientKey);
    const titles = parseStructureList(subtask?.title || "");

    if (!titles.length) {
      setEditTicketError("Every subtask needs a title.");
      return;
    }

    if (titles.some((title) => title.length > 200)) {
      setEditTicketError("Each subtask title must be 200 characters or fewer.");
      return;
    }

    if (!subtask.id && titles.length > 1) {
      setEditSubtasks((current) => current.flatMap((item) => {
        if (item.clientKey !== clientKey) return [item];
        return titles.map((title, index) => ({
          ...item,
          clientKey: index === 0 ? clientKey : `new-${crypto.randomUUID()}`,
          title,
          description: index === 0 ? item.description : "",
        }));
      }));
    } else if (!subtask.id && titles[0] !== subtask.title) {
      updateEditSubtask(clientKey, "title", titles[0]);
    }

    setEditTicketError(null);
    setEditingSubtaskKey(null);
  }

  function cancelEditSubtask(clientKey) {
    const draft = editSubtasks.find((item) => item.clientKey === clientKey);

    if (!draft?.id) {
      removeEditSubtask(clientKey);
      return;
    }

    const original = subtasks.find((subtask) => subtask.id === draft.id);
    if (original) {
      setEditSubtasks((current) =>
        current.map((subtask) =>
          subtask.clientKey === clientKey
            ? { ...original, clientKey }
            : subtask
        )
      );
    }
    setEditingSubtaskKey(null);
    setEditTicketError(null);
  }

  function startChangingStatus() {
    if (!selectedTicket) {
      return;
    }

    if (!editingTicket && !progressSessionActive) {
      initializeDrawerDrafts();
      setProgressSessionActive(true);
    }
    if (!statusChanged) {
      setStatusForm({ status: selectedTicket.status, status_note: "" });
    }
    setStatusChangeError(null);
    setChangingStatus(true);
  }

  function cancelChangingStatus() {
    setStatusChangeError(null);
    setStatusForm({ status: selectedTicket.status, status_note: "" });
    setChangingStatus(false);
    if (!editingTicket && !hasStagedStructureChanges()) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
  }

  function selectTicketStatus(status) {
    setStatusForm({ status, status_note: "" });
    setScopeResolutionChoice(["review", "done", "cancelled"].includes(status) ? status : null);
    setStatusChangeError(null);
    setChangingStatus(false);
  }

  function selectFinalScopeResolution(choice) {
    setScopeResolutionChoice(choice);
    setStatusForm({
      status: choice === "keep" ? selectedTicket.status : choice,
      status_note: "",
    });
    setStatusChangeError(null);
  }

  function reviewDrawerChanges({ closeAfter = false } = {}) {
    // Preserve a written progress update by carrying it into the reviewed note
    // only when the user has not already supplied different commit context.
    if (!drawerSessionNote.trim() && newTicketUpdate.trim()) {
      setDrawerSessionNote(newTicketUpdate.trim());
    }
    const stagedResolution = ["review", "done", "cancelled"].includes(statusForm.status) &&
      statusForm.status !== selectedTicket.status
      ? statusForm.status
      : null;
    const defaultResolution = scopeResolutionChoice || stagedResolution ||
      (finalScopeResolutionRequired ? "done" : null);
    setScopeResolutionChoice(defaultResolution);
    if (!scopeResolutionChoice && !stagedResolution && finalScopeResolutionRequired) {
      setStatusForm({ status: "done", status_note: "" });
    }
    setCloseAfterCommit(closeAfter);
    setStagedCommitSection("Ticket");
  }

  // Ticket creation and optional draft review actions.
  function initializeNewTicketDraft({ description = "" } = {}) {
    const draft = {
      title: "",
      description,
      priority: "medium",
      ticket_type: "task",
      project_id: effectiveDefaultProjectId,
      ai_context_enabled: true,
    };

    setNewTicketRecovered(false);
    setAIReview(null);
    setAIReviewError(null);
    setNewTicketForm(draft);
    setNewTicketError(null);
    setDraftReview(null);
    setDraftReviewLoading(false);
    setDraftReviewOptions({
      apply_title: true,
      apply_description: true,
      apply_priority: true,
      apply_ticket_type: true,
    });
    setSelectedDraftSubtasks([]);
    setSelectedDraftCriteria([]);
    setSelectedDraftSubtaskRevisions([]);
    setSelectedDraftCriterionRevisions([]);
    setNewTicketSubtasks([]);
    setNewTicketCriteria([]);
    setNewSubtaskInput("");
    setNewCriterionInput("");
    setCreatingTicket(true);
    return draft;
  }

  function openNewTicket() {
    directGuidedTicketDraft.current = false;
    initializeNewTicketDraft();
  }

  function openGuidedTicketDraft(ticket) {
    initializeNewTicketDraft({
      description: ticket.description || ticket.source_text || "",
    });
    setNewTicketForm({
      title: ticket.title || "",
      description: ticket.description || ticket.source_text || "",
      priority: ticket.priority || "medium",
      ticket_type: ticket.ticket_type || "task",
      project_id: ticket.project_id,
      ai_context_enabled: true,
    });
    setNewTicketCriteria((ticket.acceptance_criteria || []).map(suggestedItemText));
    setNewTicketSubtasks(
      (ticket.subtasks || []).map((item) => ({ title: suggestedItemText(item), description: null }))
    );
  }

  async function startGuidedWorkIntake(sourceText, options = {}) {
    return proposeWorkIntake(sourceText, options);
  }

  async function refineGuidedWorkIntake(attemptId, answers) {
    return refineWorkIntake(attemptId, answers);
  }

  function continueGuidedWorkIntake(sourceText, proposal, ticketIndex = 0) {
    if (proposal.action === "create_project" && proposal.proposed_project) {
      directGuidedTicketDraft.current = false;
      const project = proposal.proposed_project;
      setProjectForm({
        name: project.name || "",
        description: project.description || sourceText,
        purpose: project.purpose || "",
        why_it_matters: project.why_it_matters || "",
        target_date: "",
        life_context: "unclassified",
        ai_context_enabled: true,
      });
      setPendingGuidedProjectTickets(
        (proposal.proposed_tickets || []).map((ticket) => ({
          ...ticket,
          source_text: sourceText,
        }))
      );
      setProjectError(null);
      setProjectFormMode("create");
      return;
    }

    if (["create_ticket", "create_tickets"].includes(proposal.action)) {
      const ticket = proposal.proposed_tickets?.[ticketIndex];
      if (!ticket) return;
      directGuidedTicketDraft.current = true;
      initializeNewTicketDraft({ description: ticket.description || sourceText });
      setNewTicketForm({
        title: ticket.title || "",
        description: ticket.description || sourceText,
        priority: ticket.priority || "medium",
        ticket_type: ticket.ticket_type || "task",
        project_id: ticket.project_id ?? proposal.target_project_id ?? null,
        ai_context_enabled: true,
      });
      setNewTicketCriteria((ticket.acceptance_criteria || []).map(suggestedItemText));
      setNewTicketSubtasks(
        (ticket.subtasks || []).map((item) => ({ title: suggestedItemText(item), description: null }))
      );
      return;
    }

    if (["update_ticket", "use_existing"].includes(proposal.action)) {
      const ticket = tickets.find((item) => item.id === proposal.target_ticket_id);
      if (ticket) openTicket(ticket);
    }
  }

  function finishGuidedTicketReview() {
    const completedProjectId = guidedTicketReviewProgress?.projectId;
    closeNewTicket();
    if (completedProjectId) {
      setSelectedTicket(null);
      resetTicketActivity();
      setActiveView("projects");
      setSelectedProjectDetailId(completedProjectId);
    }
  }

  function skipGuidedTicket() {
    if (pendingGuidedProjectTickets.length) {
      const [nextTicket, ...remainingTickets] = pendingGuidedProjectTickets;
      setPendingGuidedProjectTickets(remainingTickets);
      setGuidedTicketReviewProgress((current) => (
        current ? { ...current, current: current.current + 1 } : null
      ));
      openGuidedTicketDraft(nextTicket);
      return;
    }
    finishGuidedTicketReview();
  }

  function closeNewTicket() {
    directGuidedTicketDraft.current = false;
    setPendingGuidedProjectTickets([]);
    setGuidedTicketReviewProgress(null);
    clearNewTicketDraft(currentUser);
    setNewTicketRecovered(false);
    const controller = draftReviewAbortController.current;
    draftReviewAbortController.current = null;
    controller?.abort();
    setDraftReviewLoading(false);
    setCreatingTicket(false);
    setNewTicketError(null);
    setDraftReview(null);
    setSelectedDraftSubtaskRevisions([]);
    setSelectedDraftCriterionRevisions([]);
    setNewTicketSubtasks([]);
    setNewTicketCriteria([]);
  }

  function addNewTicketSubtask(event) {
    event.preventDefault();
    const titles = appendUniqueStructureItems(
      newTicketSubtasks,
      parseStructureList(newSubtaskInput),
      (subtask) => subtask.title,
    );
    if (!titles.length) return;
    if (titles.some((title) => title.length > 200)) {
      setNewTicketError("Each subtask title must be 200 characters or fewer.");
      return;
    }
    setNewTicketSubtasks((current) => [
      ...current,
      ...titles.map((title) => ({ title, description: null })),
    ]);
    setNewSubtaskInput("");
    setNewTicketError(null);
  }

  function addNewTicketCriterion(event) {
    event.preventDefault();
    const criteria = appendUniqueStructureItems(
      newTicketCriteria,
      parseStructureList(newCriterionInput),
      (criterion) => criterion,
    );
    if (!criteria.length) return;
    setNewTicketCriteria((current) => [...current, ...criteria]);
    setNewCriterionInput("");
    setNewTicketError(null);
  }

  function removeNewTicketCriterion(index) {
    setNewTicketCriteria((current) =>
      current.filter((_, itemIndex) => itemIndex !== index)
    );
  }

  function removeNewTicketSubtask(index) {
    setNewTicketSubtasks((current) =>
      current.filter((_, itemIndex) => itemIndex !== index)
    );
  }

  function buildNewTicketPayload() {
    return {
      ...newTicketForm,
      title:
        draftReviewOptions.apply_title && draftReview?.suggested_title
          ? draftReview.suggested_title.trim()
          : newTicketForm.title.trim(),
      description:
        draftReviewOptions.apply_description &&
        draftReview?.suggested_description
          ? draftReview.suggested_description.trim()
          : newTicketForm.description.trim() || null,
      priority:
        draftReviewOptions.apply_priority && draftReview?.suggested_priority
          ? draftReview.suggested_priority
          : newTicketForm.priority,
      ticket_type:
        draftReviewOptions.apply_ticket_type &&
        draftReview?.suggested_ticket_type
          ? draftReview.suggested_ticket_type
          : newTicketForm.ticket_type,
    };
  }

  async function saveNewTicket(useDraftReview = false) {
    const ticketPayload = useDraftReview
      ? buildNewTicketPayload()
      : {
          ...newTicketForm,
          title: newTicketForm.title.trim(),
          description: newTicketForm.description.trim() || null,
        };

    if (ticketPayload.ai_context_enabled !== false) {
      delete ticketPayload.ai_context_enabled;
    }

    if (!ticketPayload.title) {
      setNewTicketError("A ticket title is required.");
      return;
    }

    setSavingNewTicket(true);
    setNewTicketError(null);
    let created = null;

    try {
      const effectiveManualSubtasks = newTicketSubtasks.map(
        (subtask, index) => {
          const revision = draftReview?.subtask_revisions?.find(
            (item) => item.source_index === index
          );

          if (
            useDraftReview &&
            revision &&
            selectedDraftSubtaskRevisions[index]
          ) {
            return {
              title: revision.suggested_title.trim(),
              description:
                revision.suggested_description?.trim() || null,
            };
          }

          return subtask;
        }
      );
      const suggestedSubtasks = useDraftReview && draftReview
        ? draftReview.suggested_subtasks.filter(
            (_, index) => selectedDraftSubtasks[index]
          )
        : [];
      const existingSubtaskTitles = new Set(
        effectiveManualSubtasks.map((subtask) => subtask.title.toLowerCase())
      );
      const subtasksToCreate = [
        ...effectiveManualSubtasks,
        ...suggestedSubtasks.filter(
          (subtask) =>
            !existingSubtaskTitles.has(subtask.title.trim().toLowerCase())
        ),
      ];

      const effectiveManualCriteria = newTicketCriteria.map(
        (criterion, index) => {
          const revision = draftReview?.acceptance_criteria_revisions?.find(
            (item) => item.source_index === index
          );

          return useDraftReview &&
            revision &&
            selectedDraftCriterionRevisions[index]
            ? revision.suggested_text.trim()
            : criterion;
        }
      );
      const suggestedCriteria = useDraftReview && draftReview
        ? draftReview.acceptance_criteria.filter(
            (_, index) => selectedDraftCriteria[index]
          ).map(suggestedItemText)
        : [];
      const existingCriteria = new Set(
        effectiveManualCriteria.map((criterion) => criterion.toLowerCase())
      );
      const criteriaToCreate = [
        ...effectiveManualCriteria,
        ...suggestedCriteria.filter(
          (criterion) =>
            !existingCriteria.has(criterion.trim().toLowerCase())
        ),
      ];

      created = await createTicket({
        ...ticketPayload,
        acceptance_criteria: criteriaToCreate.map((text, index) => ({
          text,
          sort_order: index + 1,
        })),
        subtasks: subtasksToCreate.map((subtask, index) => ({
          title: subtask.title,
          description: subtask.description || null,
          sort_order: index + 1,
        })),
      });

      setTickets((current) => [
        created,
        ...current,
      ]);

      if (pendingGuidedProjectTickets.length) {
        const [nextTicket, ...remainingTickets] = pendingGuidedProjectTickets;
        setPendingGuidedProjectTickets(remainingTickets);
        setGuidedTicketReviewProgress((current) => (
          current ? { ...current, current: current.current + 1 } : null
        ));
        openGuidedTicketDraft(nextTicket);
      } else if (guidedTicketReviewProgress) {
        finishGuidedTicketReview();
      } else if (directGuidedTicketDraft.current) {
        directGuidedTicketDraft.current = false;
        setGuidedIntakeResetVersion((current) => current + 1);
        clearNewTicketDraft(currentUser);
        setCreatingTicket(false);
        await openTicket(created);
      } else {
        setCreatingTicket(false);
        await openTicket(created);
      }
    } catch (err) {
      if (created) {
        setCreatingTicket(false);
        await openTicket(created);
        setAIReviewError(
          `The ticket was created, but some selected details could not be created: ${err.message}`
        );
        return;
      }

      setNewTicketError(err.message);
    } finally {
      setSavingNewTicket(false);
    }
  }

  async function reviewNewTicketDraft() {
    if (
      !newTicketForm.title.trim() &&
      !newTicketForm.description.trim()
    ) {
      setNewTicketError(
        "Add a title or description before reviewing with Telaryn."
      );
      return;
    }

    const controller = new AbortController();
    draftReviewAbortController.current = controller;
    setDraftReviewLoading(true);
    setNewTicketError(null);

    try {
      const { ai_context_enabled, ...draftFields } = newTicketForm;
      const review = await reviewTicketDraft(
        {
          ...draftFields,
          ...(ai_context_enabled === false ? { ai_context_enabled: false } : {}),
          title: newTicketForm.title.trim(),
          description: newTicketForm.description.trim() || null,
          subtasks: newTicketSubtasks,
          acceptance_criteria: newTicketCriteria,
        },
        { signal: controller.signal },
      );

      setDraftReview(review);
      setSelectedDraftSubtasks(
        review.suggested_subtasks.map(() => true)
      );
      setSelectedDraftCriteria(
        review.acceptance_criteria.map(() => true)
      );
      setSelectedDraftSubtaskRevisions(
        newTicketSubtasks.map(() => false)
      );
      setSelectedDraftCriterionRevisions(
        newTicketCriteria.map(() => false)
      );
    } catch (err) {
      if (draftReviewAbortController.current === controller) {
        setNewTicketError(err.message);
      }
    } finally {
      if (draftReviewAbortController.current === controller) {
        draftReviewAbortController.current = null;
        setDraftReviewLoading(false);
      }
    }
  }

  function cancelDraftReview() {
    draftReviewAbortController.current?.abort();
  }

  function toggleDraftReviewOption(name) {
    setDraftReviewOptions((current) => ({
      ...current,
      [name]: !current[name],
    }));
  }

  function toggleDraftSubtask(index) {
    setSelectedDraftSubtasks((current) =>
      current.map((selected, itemIndex) =>
        itemIndex === index ? !selected : selected
      )
    );
  }

  function toggleDraftCriterion(index) {
    setSelectedDraftCriteria((current) =>
      current.map((selected, itemIndex) =>
        itemIndex === index ? !selected : selected
      )
    );
  }

  function toggleDraftSubtaskRevision(index) {
    setSelectedDraftSubtaskRevisions((current) =>
      current.map((selected, itemIndex) =>
        itemIndex === index ? !selected : selected
      )
    );
  }

  function toggleDraftCriterionRevision(index) {
    setSelectedDraftCriterionRevisions((current) =>
      current.map((selected, itemIndex) =>
        itemIndex === index ? !selected : selected
      )
    );
  }

  function returnToNewTicketDraft() {
    setDraftReview(null);
    setSelectedDraftSubtaskRevisions([]);
    setSelectedDraftCriterionRevisions([]);
    setNewTicketError(null);
  }

  // Persisted ticket edits, status transitions, and progress updates.
  function offerProgressReview(evidence, evidenceType, evidenceId = null) {
    if (!evidence?.trim() || selectedTicket?.ai_context_enabled === false) return;
    const project = projects.find((item) => item.id === selectedTicket?.project_id);
    if (project?.ai_context_enabled === false) return;
    setProgressReviewPrompt({ evidence: evidence.trim(), evidence_type: evidenceType, evidence_id: evidenceId });
    setProgressReview(null); setSelectedProgressSuggestions([]); setProgressReviewError(null);
  }

  async function runProgressReview() {
    if (!selectedTicket || !progressReviewPrompt) return;
    setProgressReviewLoading(true); setProgressReviewError(null);
    try {
      const result = await createProgressReview(selectedTicket.id, progressReviewPrompt);
      setProgressReview(result);
      setSelectedProgressSuggestions(result.suggestions.map((item) => item.key));
    } catch (error) { setProgressReviewError(error.message); }
    finally { setProgressReviewLoading(false); }
  }

  async function dismissProgressReview() {
    if (selectedTicket && progressReview?.id) {
      try { await rejectProgressReview(selectedTicket.id, progressReview.id); } catch { /* dismissal never blocks work */ }
    }
    setProgressReviewPrompt(null); setProgressReview(null); setSelectedProgressSuggestions([]); setProgressReviewError(null);
  }

  async function applyProgressReview() {
    if (!selectedTicket || !progressReview) return;
    setProgressReviewApplying(true); setProgressReviewError(null);
    try {
      const result = await acceptProgressReview(
        selectedTicket.id,
        progressReview.id,
        selectedProgressSuggestions,
      );
      const [criteria, taskItems] = await Promise.all([
        getAcceptanceCriteria(selectedTicket.id), getSubtasks(selectedTicket.id),
      ]);
      setAcceptanceCriteria(criteria); setSubtasks(taskItems);
      await refreshTicketActivity(selectedTicket.id);
      const appliedCount = result.applied_progress?.applied?.length || 0;
      const staleCount = result.applied_progress?.stale?.length || 0;
      if (appliedCount === 0) {
        setProgressReview(result);
        setSelectedProgressSuggestions([]);
        setProgressReviewError(
          staleCount
            ? "The selected work changed after Telaryn reviewed it, so nothing was marked complete. Review the current Ticket and try again."
            : "No progress items were applied.",
        );
        return;
      }
      setTickets((current) => current.map((ticket) =>
        ticket.id === selectedTicket.id
          ? { ...ticket, updated_at: new Date().toISOString() }
          : ticket
      ));
      setRecoveryNotice(
        `${appliedCount} ${appliedCount === 1 ? "item was" : "items were"} marked complete by your approved Telaryn review.${staleCount ? ` ${staleCount} changed item was skipped.` : ""}`,
      );
      setProgressReviewPrompt(null); setProgressReview(null); setSelectedProgressSuggestions([]);
    } catch (error) { setProgressReviewError(error.message); }
    finally { setProgressReviewApplying(false); }
  }

  // Commits the complete drawer session from one review decision. The existing
  // Grouped structure endpoints make each collection atomic and produce one
  // useful activity record instead of a burst of generic item requests.
  async function commitDrawerSession() {
    if (!selectedTicket || savingTicketEdits || drawerSessionChanges.length === 0) return;
    if (!editForm.title.trim()) {
      setEditTicketError("A ticket title is required.");
      setStagedCommitSection(null);
      return;
    }
    if (editAcceptanceCriteria.some((item) => !item.text.trim())) {
      setAcceptanceCriteriaError("Every acceptance criterion needs text.");
      setStagedCommitSection(null);
      return;
    }
    if (editSubtasks.some((item) => !item.title.trim())) {
      setEditTicketError("Every subtask needs a title.");
      setStagedCommitSection(null);
      return;
    }

    const committedEvidence = newTicketUpdate.trim() || drawerSessionNote.trim();
    setSavingTicketEdits(true);
    setEditTicketError(null);
    setAcceptanceCriteriaError(null);
    try {
      const { ai_context_enabled, ...ticketFields } = editForm;
      const result = await saveDrawerSession(selectedTicket.id, {
        ticket: {
          ...ticketFields,
          ...(ai_context_enabled === false ? { ai_context_enabled: false } : {}),
          status: statusForm.status,
          title: editForm.title.trim(),
          description: editForm.description.trim() || null,
        },
        acceptance_criteria: editAcceptanceCriteria.map((item) => ({
            id: item.id || null,
            text: item.text.trim(),
            completed: Boolean(item.completed),
            deferred: Boolean(item.deferred),
        })),
        subtasks: editSubtasks.map((item) => ({
            id: item.id || null,
            title: item.title.trim(),
            description: item.description?.trim() || null,
            status: item.status,
        })),
        note: drawerSessionNote.trim() || null,
        update_content: newTicketUpdate.trim() || null,
      });
      const updatedTicket = result.ticket;
      const updatedCriteria = result.acceptance_criteria;
      const updatedSubtasks = result.subtasks;
      setTickets((current) => current.map((item) => item.id === updatedTicket.id ? updatedTicket : item));
      setSelectedTicket(updatedTicket);
      setAcceptanceCriteria(updatedCriteria);
      setSubtasks(updatedSubtasks);
      await refreshTicketActivity(selectedTicket.id);
      if (newTicketUpdate.trim()) cancelAddingTicketUpdate();
      if (committedEvidence) offerProgressReview(committedEvidence, "drawer_session");
      const shouldClose = closeAfterCommit ||
        (selectedTicket.status !== "done" && updatedTicket.status === "done");
      cancelEditingTicket();
      if (shouldClose) closeTicket();
    } catch (err) {
      setEditTicketError(`Telaryn could not commit the drawer session: ${err.message}`);
      setStagedCommitSection(null);
    } finally {
      setSavingTicketEdits(false);
    }
  }

  async function saveTicketUpdate(event) {
    if (!selectedTicket) {
      return;
    }

    const created = await recordTicketUpdate(event, selectedTicket.id);
    if (!created) {
      return;
    }

    setSelectedTicket((current) => ({
      ...current,
      updated_at: created.created_at,
    }));
    setTickets((current) =>
      current.map((ticket) =>
        ticket.id === selectedTicket.id
          ? { ...ticket, updated_at: created.created_at }
          : ticket
      )
    );
    offerProgressReview(created.content, "ticket_update", created.id);
  }

  // Existing-ticket AI review remains a proposal until explicit acceptance.
  async function runAIReview() {
    if (!selectedTicket || aiReviewRequestRunning.current) {
      return;
    }

    const controller = new AbortController();
    aiReviewAbortController.current = controller;
    aiReviewRequestRunning.current = true;
    setAIReviewLoading(true);
    setAIReviewError(null);
    setAIReview(null);

    try {
      const review = await createAIReview(
        selectedTicket.id,
        { signal: controller.signal },
      );
      setAIReview(review);
      setSelectedReviewCriteria(
        review.acceptance_criteria.map(() => true)
      );
    } catch (err) {
      if (aiReviewAbortController.current === controller) {
        setAIReviewError(err.message);
      }
    } finally {
      if (aiReviewAbortController.current === controller) {
        aiReviewAbortController.current = null;
        aiReviewRequestRunning.current = false;
        setAIReviewLoading(false);
      }
    }
  }

  function cancelAIReview() {
    aiReviewAbortController.current?.abort();
  }

  function toggleReviewOption(name) {
    setReviewOptions((current) => ({
      ...current,
      [name]: !current[name],
    }));
  }

  function toggleReviewCriterion(index) {
    setSelectedReviewCriteria((current) =>
      current.map((selected, itemIndex) =>
        itemIndex === index ? !selected : selected
      )
    );
  }

  async function applyAIReview() {
    if (
      !selectedTicket ||
      !aiReview ||
      applyReviewRequestRunning.current
    ) {
      return;
    }

    applyReviewRequestRunning.current = true;
    setApplyingReview(true);
    setAIReviewError(null);

    try {
      await acceptAIReview(
        selectedTicket.id,
        aiReview.id,
        {
          ...reviewOptions,
          acceptance_criteria_indices: selectedReviewCriteria
            .map((selected, index) => (selected ? index : null))
            .filter((index) => index !== null),
        }
      );

      const [updatedTickets, updatedSubtasks, updatedCriteria] =
        await Promise.all([
          getTickets(),
          getSubtasks(selectedTicket.id),
          getAcceptanceCriteria(selectedTicket.id),
        ]);

      setTickets(updatedTickets);
      setSubtasks(updatedSubtasks);
      setAcceptanceCriteria(updatedCriteria);
      await refreshTicketActivity(selectedTicket.id);

      const refreshedTicket = updatedTickets.find(
        (ticket) => ticket.id === selectedTicket.id
      );

      setSelectedTicket(refreshedTicket);
      setAIReview(null);
    } catch (err) {
      setAIReviewError(err.message);
    } finally {
      applyReviewRequestRunning.current = false;
      setApplyingReview(false);
    }
  }

  // Ticket selection and completion toggles refresh only the affected detail state.
  async function openTicket(ticket, progressChange = null) {
    const requestId = drawerRequestVersion.current + 1;
    drawerRequestVersion.current = requestId;
    setProgressReviewPrompt(null); setProgressReview(null);
    setSelectedProgressSuggestions([]); setProgressReviewError(null);
    setAIReview(null);
    setSelectedReviewCriteria([]);
    setAIReviewError(null);
    setEditingTicket(false);
    setEditTicketError(null);
    setChangingStatus(false);
    setStatusChangeError(null);
    setStatusForm({ status: ticket.status, status_note: "" });
    resetTicketActivity();
    setProgressSessionActive(false);
    setDrawerSessionNote("");
    setScopeResolutionChoice(null);
    setDrawerFocusPending(false);
    setDrawerFocusNotice(null);
    setDrawerFocusError(null);

    setSelectedTicket(ticket);
    setDrawerRelatedState("loading");
    setSubtasks([]);
    setSubtasksError(null);
    setAcceptanceCriteria([]);
    setAcceptanceCriteriaError(null);
    setNewCriterionText("");
    setSubtasksLoading(true);
    setAcceptanceCriteriaLoading(true);

    const [subtaskResult, criteriaResult] = await Promise.allSettled([
      getSubtasks(ticket.id),
      getAcceptanceCriteria(ticket.id),
      loadTicketActivity(ticket.id),
    ]);

    if (drawerRequestVersion.current !== requestId) return;

    if (subtaskResult.status === "fulfilled") {
      setSubtasks(subtaskResult.value);
    } else {
      setSubtasksError(subtaskResult.reason.message);
    }

    if (criteriaResult.status === "fulfilled") {
      setAcceptanceCriteria(criteriaResult.value);
    } else {
      setAcceptanceCriteriaError(criteriaResult.reason.message);
    }

    if (
      progressChange &&
      subtaskResult.status === "fulfilled" &&
      criteriaResult.status === "fulfilled"
    ) {
      initializeDrawerDrafts(
        progressChange,
        ticket,
        criteriaResult.value,
        subtaskResult.value,
      );
      setProgressSessionActive(true);
    }

    setSubtasksLoading(false);
    setAcceptanceCriteriaLoading(false);
    setDrawerRelatedState("ready");
  }

  function completeRemainingAcceptanceCriteria() {
    if (!selectedTicket || acceptanceCriteriaLoading || editingCriterionKey !== null) return;

    const sessionActive = editingTicket || progressSessionActive;
    const criteriaSource = sessionActive
      ? editAcceptanceCriteria
      : acceptanceCriteria;
    const subtasksSource = sessionActive ? editSubtasks : subtasks;
    const nextCriteria = completeRemainingCriteria(criteriaSource);

    if (sessionActive) {
      setEditAcceptanceCriteria(nextCriteria);
    } else {
      initializeDrawerDrafts(
        null,
        selectedTicket,
        nextCriteria,
        subtasksSource,
      );
      setProgressSessionActive(true);
    }
    setScopeResolutionChoice(null);
  }

  function completeRemainingTicketSubtasks() {
    if (!selectedTicket || subtasksLoading || editingSubtaskKey !== null) return;

    const sessionActive = editingTicket || progressSessionActive;
    const criteriaSource = sessionActive
      ? editAcceptanceCriteria
      : acceptanceCriteria;
    const subtasksSource = sessionActive ? editSubtasks : subtasks;
    const nextSubtasks = completeRemainingSubtasks(subtasksSource);

    if (sessionActive) {
      setEditSubtasks(nextSubtasks);
    } else {
      initializeDrawerDrafts(
        null,
        selectedTicket,
        criteriaSource,
        nextSubtasks,
      );
      setProgressSessionActive(true);
    }
    setScopeResolutionChoice(null);
  }

  function toggleAcceptanceCriterion(criterion) {
    if (criterion.deferred) return;
    if (!editingTicket && !progressSessionActive) {
      initializeDrawerDrafts({ criterionId: criterion.id });
      setProgressSessionActive(true);
      return;
    }
    const nextCriteria = editAcceptanceCriteria.map((item) =>
      item.id === criterion.id ? { ...item, completed: !item.completed } : item
    );
    setEditAcceptanceCriteria(nextCriteria);
    if (!editingTicket && statusForm.status === selectedTicket.status && !hasStagedStructureChanges(nextCriteria, editSubtasks)) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
    if (!editingTicket && statusForm.status === selectedTicket.status && !hasStagedStructureChanges(nextCriteria, editSubtasks)) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
  }

  function toggleAcceptanceCriterionDeferred(criterion) {
    if (!editingTicket && !progressSessionActive) {
      initializeDrawerDrafts({ deferCriterionId: criterion.id });
      setProgressSessionActive(true);
      return;
    }
    const nextCriteria = editAcceptanceCriteria.map((item) =>
      item.id === criterion.id
        ? { ...item, deferred: !item.deferred, completed: false }
        : item
    );
    setEditAcceptanceCriteria(nextCriteria);
  }

  function toggleSubtask(subtask) {
    if (subtask.status === "deferred") return;
    if (!editingTicket && !progressSessionActive) {
      initializeDrawerDrafts({ subtaskId: subtask.id });
      setProgressSessionActive(true);
      return;
    }
    const nextSubtasks = editSubtasks.map((item) =>
      item.id === subtask.id
        ? { ...item, status: item.status === "done" ? "todo" : "done" }
        : item
    );
    setEditSubtasks(nextSubtasks);
    if (!editingTicket && statusForm.status === selectedTicket.status && !hasStagedStructureChanges(editAcceptanceCriteria, nextSubtasks)) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
  }

  function toggleSubtaskDeferred(subtask) {
    if (!editingTicket && !progressSessionActive) {
      initializeDrawerDrafts({ deferSubtaskId: subtask.id });
      setProgressSessionActive(true);
      return;
    }
    const nextSubtasks = editSubtasks.map((item) =>
      item.id === subtask.id
        ? { ...item, status: item.status === "deferred" ? "todo" : "deferred" }
        : item
    );
    setEditSubtasks(nextSubtasks);
    if (!editingTicket && statusForm.status === selectedTicket.status && !hasStagedStructureChanges(editAcceptanceCriteria, nextSubtasks)) {
      setProgressSessionActive(false);
      setDrawerSessionNote("");
    }
  }

  // Closing is guarded while a workflow could otherwise lose unsaved work.
  const closeTicket = useCallback(() => {
    document.activeElement?.blur?.();
    drawerRequestVersion.current += 1;
    const controller = aiReviewAbortController.current;
    aiReviewAbortController.current = null;
    controller?.abort();
    aiReviewRequestRunning.current = false;
    setAIReviewLoading(false);
    setProgressReviewPrompt(null); setProgressReview(null);
    setSelectedProgressSuggestions([]); setProgressReviewError(null);
    setSelectedTicket(null);
    setRecoveryNotice(null);
    setDrawerFocusPending(false);
    setDrawerFocusNotice(null);
    setDrawerFocusError(null);
    setSubtasks([]);
    setSubtasksLoading(false);
    setSubtasksError(null);
    setAcceptanceCriteria([]);
    setAcceptanceCriteriaLoading(false);
    setAcceptanceCriteriaError(null);
    setDrawerRelatedState("idle");
    setNewCriterionText("");
    setAIReview(null);
    setSelectedReviewCriteria([]);
    setAIReviewError(null);
    setEditingTicket(false);
    setEditingAcceptanceCriteria(false);
    setEditingSubtasks(false);
    setEditSubtasks([]);
    setEditAcceptanceCriteria([]);
    setEditingSubtaskKey(null);
    setEditingCriterionKey(null);
    setSavingTicketEdits(false);
    setStagedCommitSection(null);
    setEditTicketError(null);
    setChangingStatus(false);
    setStatusChangeError(null);
    resetTicketActivity();
    setProgressSessionActive(false);
    setDrawerSessionNote("");
    setScopeResolutionChoice(null);
  }, [resetTicketActivity]);

  function requestCloseTicket() {
    if ((editingTicket || progressSessionActive) && drawerSessionChanges.length > 0) {
      reviewDrawerChanges({ closeAfter: true });
      return;
    }
    if (editingTicket || progressSessionActive) cancelEditingTicket();
    closeTicket();
  }

  useEffect(() => {
    function handleTicketDrawerKeyDown(event) {
      if (
        event.key !== "Escape" ||
        !selectedTicket ||
        editingTicket ||
        editingAcceptanceCriteria ||
        editingSubtasks ||
        changingStatus ||
        addingTicketUpdate ||
        aiReview ||
        aiReviewLoading ||
        applyingReview
      ) {
        return;
      }

      if (progressSessionActive && drawerSessionChanges.length > 0) {
        setCloseAfterCommit(true);
        setStagedCommitSection("Ticket");
        return;
      }

      closeTicket();
    }

    window.addEventListener("keydown", handleTicketDrawerKeyDown);
    return () => window.removeEventListener("keydown", handleTicketDrawerKeyDown);
  }, [
    selectedTicket,
    progressSessionActive,
    drawerSessionChanges,
    editingTicket,
    editingAcceptanceCriteria,
    editingSubtasks,
    changingStatus,
    addingTicketUpdate,
    aiReview,
    aiReviewLoading,
    applyingReview,
    closeTicket,
  ]);

  // View composition: focused components render from this coordinator's state.
  if (authChecking) {
    return <div className="status-screen">Checking Telaryn session...</div>;
  }

  const invitationMatch = window.location.hash.match(/^#\/accept-invitation\?(.+)$/);
  const invitationToken = invitationMatch
    ? new URLSearchParams(invitationMatch[1]).get("token")
    : null;

  if (invitationToken && (!showLogin || currentUser)) {
    return <InvitationAcceptanceView
      token={invitationToken}
      currentUser={currentUser}
      onSignIn={() => { setAuthError(null); setShowLogin(true); }}
      onComplete={() => {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
        if (currentUser) window.location.reload();
        else setShowLogin(true);
      }}
    />;
  }

  if (!currentUser) {
    if (showLogin) return <LoginView
      error={authError}
      submitting={authSubmitting}
      onLogin={submitLogin}
      onCancel={() => { setAuthError(null); setShowLogin(false); }}
    />;
    const onSignIn = () => { setAuthError(null); setShowLogin(true); };
    if (publicPage === "privacy" || publicPage === "terms") {
      return <PublicPolicyView policy={publicPage} onSignIn={onSignIn} />;
    }
    if (publicPage === "getting-started") {
      return <GettingStartedView onSignIn={onSignIn} />;
    }
    return <PublicLandingView onSignIn={onSignIn} />;
  }

  if (loading) {
    return <div className="status-screen">Loading Telaryn...</div>;
  }

  if (error) {
    return <div className="status-screen error">{error}</div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <AtlasBrand className="sidebar-brand" />

        <div className="sidebar-navigation">
          <nav>
          <button
            className={`nav-item ${activeView === "work" ? "active" : ""}`}
            onClick={() => setActiveView("work")}
          >
            My Work
          </button>
          {activeView === "work" && (
            <div className="my-work-subnav" role="group" aria-label="My Work sections">
              {MY_WORK_SECTIONS.map((section) => (
                <button
                  key={section.id}
                  type="button"
                  className={activeMyWorkSection === section.id ? "active" : ""}
                  aria-current={activeMyWorkSection === section.id ? "location" : undefined}
                  onClick={() => navigateToMyWorkSection(section.id)}
                >
                  {section.label}
                </button>
              ))}
            </div>
          )}

          <button
            className={`nav-item ${activeView === "projects" ? "active" : ""}`}
            onClick={openProjectsView}
          >
            Projects
          </button>

          <button
            className={`nav-item ${activeView === "search" ? "active" : ""}`}
            onClick={() => setActiveView("search")}
          >
            Search
          </button>

          <button
            className={`nav-item ${activeView === "reports" ? "active" : ""}`}
            onClick={() => setActiveView("reports")}
          >
            Reports
          </button>
          </nav>

          <div className="sidebar-spacer" />

          <button
            className="new-ticket-button"
            onClick={openNewTicket}
          >
            + New Ticket
          </button>

          <nav className="secondary-nav" aria-label="Application">
          {intakeNavigation.allowed && <button
            className={`nav-item ${activeView === "access-requests" ? "active" : ""}`}
            onClick={() => setActiveView("access-requests")}
          >Access Requests <span className="intake-count" aria-label={`${intakeNavigation.count} new requests`}>{intakeNavigation.count}</span></button>}
          {deploymentAdminAllowed && <button
            className={`nav-item ${activeView === "user-management" ? "active" : ""}`}
            onClick={() => setActiveView("user-management")}
          >User Management</button>}
          {feedbackReviewerAllowed && <button
            className={`nav-item ${activeView === "feedback-admin" ? "active" : ""}`}
            onClick={() => setActiveView("feedback-admin")}
          >Feedback Review</button>}
          <button
            className={`nav-item ${activeView === "getting-started" ? "active" : ""}`}
            onClick={() => setActiveView("getting-started")}
          >Getting Started</button>
          <button
            className={`nav-item ${activeView === "feedback" ? "active" : ""}`}
            onClick={openFeedbackView}
          >Send Feedback</button>
          <button
            className={`nav-item ${activeView === "settings" ? "active" : ""}`}
            onClick={() => setActiveView("settings")}
          >
            Settings
          </button>
          <button
            className={`nav-item about-nav ${activeView === "about" ? "active" : ""}`}
            onClick={() => setActiveView("about")}
          >
            About Telaryn
          </button>
          </nav>
        </div>

        <div className="session-summary">
          <div className="session-avatar" aria-hidden="true">
            {currentUser.display_name.trim().charAt(0).toUpperCase()}
          </div>
          <div className="session-identity">
            <strong>{currentUser.display_name}</strong>
            <span>{currentUser.workspace_name}</span>
          </div>
          <button type="button" onClick={endSession}>Sign Out</button>
        </div>
      </aside>

      {mobileExecutionMode && (
        <nav className="mobile-execution-nav" aria-label="Mobile navigation">
          <button
            className={activeView === "work" ? "active" : ""}
            type="button"
            onClick={() => setActiveView("work")}
          >
            <span className="mobile-nav-icon" aria-hidden="true">✓</span>
            <span>Work</span>
          </button>
          <button
            className={activeView === "projects" ? "active" : ""}
            type="button"
            onClick={openProjectsView}
          >
            <span className="mobile-nav-icon" aria-hidden="true">▦</span>
            <span>Projects</span>
          </button>
          <button className="mobile-new-ticket" type="button" onClick={openNewTicket} aria-label="New Ticket">
            <span className="mobile-new-ticket-icon" aria-hidden="true">+</span>
            <span>New</span>
          </button>
          <button
            className={activeView === "search" ? "active" : ""}
            type="button"
            onClick={() => setActiveView("search")}
          >
            <span className="mobile-nav-icon" aria-hidden="true">⌕</span>
            <span>Search</span>
          </button>
          <details className="mobile-more" ref={mobileMoreRef}>
            <summary className={["reports", "access-requests", "user-management", "feedback-admin", "feedback", "settings", "about", "getting-started"].includes(activeView) ? "active" : ""}>
              <span className="mobile-nav-icon" aria-hidden="true">•••</span>
              <span>More</span>
            </summary>
            <div className="mobile-more-menu">
              <span className="mobile-more-identity">{currentUser.display_name}<small>{currentUser.workspace_name}</small></span>
              <button className={activeView === "reports" ? "active" : ""} type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("reports");
              }}>Reports</button>
              {intakeNavigation.allowed && <button type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("access-requests");
              }}>Access Requests <span className="intake-count" aria-label={`${intakeNavigation.count} new requests`}>{intakeNavigation.count}</span></button>}
              {deploymentAdminAllowed && <button type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("user-management");
              }}>User Management</button>}
              {feedbackReviewerAllowed && <button type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("feedback-admin");
              }}>Feedback Review</button>}
              <button className={activeView === "feedback" ? "active" : ""} type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                openFeedbackView();
              }}>Send Feedback</button>
              <button className={activeView === "getting-started" ? "active" : ""} type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("getting-started");
              }}>Getting Started</button>
              <button type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("settings");
              }}>Settings</button>
              <button type="button" onClick={(event) => {
                event.currentTarget.closest("details").open = false;
                setActiveView("about");
              }}>About Telaryn</button>
              <button type="button" onClick={endSession}>Sign Out</button>
            </div>
          </details>
        </nav>
      )}

    {activeView === "work" && (
      <MyWorkView
        work={myWork}
        loading={myWorkLoading}
        error={myWorkError}
        canUndoFocus={focusUndo?.source === "work" && focusUndo.currentId === myWork?.current_focus?.id}
        onOpenTicket={(workItem) => {
          const ticket = tickets.find((item) => item.id === workItem.id);
          if (ticket) openTicket(ticket);
        }}
        onSetFocus={setCurrentFocus}
        onUndoFocus={undoCurrentFocus}
        onSetAvailability={setWorkAvailability}
        onMakeAvailable={(workItem) =>
          setWorkAvailability(workItem, "available", null)
        }
        onStartGuidedIntake={startGuidedWorkIntake}
        onRefineGuidedIntake={refineGuidedWorkIntake}
        onRecoverGuidedIntake={getCurrentWorkIntake}
        onGetGuidedIntake={getWorkIntake}
        onCancelGuidedIntake={cancelWorkIntake}
        onDismissGuidedIntake={dismissWorkIntake}
        onContinueGuidedIntake={continueGuidedWorkIntake}
        guidedIntakeResetVersion={guidedIntakeResetVersion}
        activeSectionId={activeMyWorkSection}
        navigationRequest={myWorkNavigationRequest}
        onActiveSectionChange={setActiveMyWorkSection}
        onNavigateSection={navigateToMyWorkSection}
        onboardingPanel={<OnboardingPanel
          progress={onboarding}
          onAction={runOnboardingAction}
          onGuide={() => setActiveView("getting-started")}
          onDismiss={() => setOnboardingDismissed(true)}
        />}
        onCompleteNextAction={(workItem) => {
          const ticket = tickets.find((item) => item.id === workItem.id);
          if (ticket && workItem.next_action) {
            openTicket(ticket, { subtaskId: workItem.next_action.subtask_id });
          }
        }}
      />
    )}

    {activeView === "projects" && (
      <ProjectsView
        key={projectsNavigationVersion}
        projects={projects}
        archivedProjects={archivedProjects}
        tickets={tickets}
        archivedTickets={archivedTickets}
        selectedProjectId={selectedProjectDetailId}
        preferredProjectId={effectiveDefaultProjectId}
        onDefaultProjectChange={changeDefaultProject}
        savingDefaultProject={savingPreference}
        defaultProjectError={preferenceError}
        currentFocusProjectId={myWork?.current_focus?.project_id || null}
        currentFocusTicketId={myWork?.current_focus?.id || null}
        onSelectProject={setSelectedProjectDetailId}
        onCreateProject={openNewProject}
        onEditProject={openProjectEditor}
        onArchiveProject={archiveSelectedProject}
        onClassifyArchivedProject={classifySelectedArchivedProject}
        onRestoreProject={restoreSelectedProject}
        projectArchivePending={projectArchivePending}
        projectArchiveError={projectArchiveError}
        onOpenTicket={openTicket}
      />
    )}

    {activeView === "search" && <SearchView onOpenResult={openSearchResult} />}

    {activeView === "reports" && (
      <ReportsView
        loadProjects={getReportProjects}
        onGenerate={generateActivityReport}
        onRequestAITransmission={requestAITransmission}
      />
    )}

    {activeView === "about" && <AboutView />}
    {activeView === "getting-started" && <GettingStartedView
      signedIn
      hasWork={tickets.length > 0 || projects.length > 0}
      progress={onboarding}
      onOpenWork={() => navigateToMyWorkSection("capture-work")}
      onShowChecklist={() => setOnboardingDismissed(false)}
    />}
    {activeView === "access-requests" && <main className="main-content">
      {intakeNavigation.allowed ? <AccessRequestReview /> : <p>Access request review is unavailable for this account.</p>}
      <button type="button" className="secondary-button" onClick={() => setActiveView("work")}>← Back to My Work</button>
    </main>}

    {activeView === "user-management" && <main className="main-content administration-view">
      {deploymentAdminAllowed ? <UserManagement /> : <p>User management is unavailable for this account.</p>}
      <button type="button" className="secondary-button" onClick={() => setActiveView("work")}>← Back to My Work</button>
    </main>}

    {activeView === "feedback" && <FeedbackView route={`/app/${feedbackSourceView}`} onBack={closeFeedbackView} />}

    {activeView === "feedback-admin" && <main className="main-content administration-view">
      {feedbackReviewerAllowed ? <FeedbackAdministration /> : <p>Feedback review is unavailable for this account.</p>}
      <button type="button" className="secondary-button" onClick={() => setActiveView("work")}>← Back to My Work</button>
    </main>}

    {activeView === "settings" && (
      <SettingsView
        theme={theme}
        onThemeChange={setTheme}
        onBackToWork={mobileExecutionMode ? () => setActiveView("work") : undefined}
      />
    )}

      {selectedTicket && (<>
        <TicketDrawer
          editing={
            editingTicket || editingAcceptanceCriteria || editingSubtasks
          }
          hideClose={Boolean(stagedCommitSection)}
          onClose={requestCloseTicket}
          footer={(editingTicket || progressSessionActive) && !changingStatus && !stagedCommitSection && drawerSessionChanges.length > 0 ? (
            <div className="inline-edit-footer">
              {editTicketError && (
                <div className="ai-review-error">{editTicketError}</div>
              )}

              <div className="inline-edit-actions">
                <span>{drawerSessionChanges.length} pending {drawerSessionChanges.length === 1 ? "change" : "changes"}</span>
                <button
                  className="secondary-button"
                  onClick={cancelEditingTicket}
                  disabled={savingTicketEdits}
                >
                  {progressSessionActive && !editingTicket ? "Undo Ticket Update" : "Cancel Editing"}
                </button>

                <button
                  className="ai-button"
                  onClick={() => reviewDrawerChanges()}
                  disabled={savingTicketEdits || editingCriterionKey !== null || editingSubtaskKey !== null}
                >
                  Review Ticket Update
                </button>
              </div>
            </div>
          ) : null}
        >
          {recoveryNotice && (
            <div className="drawer-recovery-notice" role="status">
              <p>{recoveryNotice}</p>
              <button type="button" className="text-button" onClick={() => setRecoveryNotice(null)}>Dismiss</button>
            </div>
          )}
          <TicketDetailsSection
            mobile={mobileExecutionMode}
            ticket={selectedTicket}
            projects={allProjects}
            projectName={getProjectName(selectedTicket.project_id)}
            readOnly={selectedTicketArchived}
            editing={editingTicket}
            editForm={editForm}
            error={editTicketError}
            canEdit={canStartTicketEditing}
            onStartEditing={startEditingTicket}
            onEditFieldChange={updateTicketEditField}
            focusState={selectedTicketFocusState}
            focusPending={drawerFocusPending}
            focusNotice={drawerFocusNotice}
            focusError={drawerFocusError}
            canUndoFocus={Boolean(
              focusUndo?.source === "drawer" &&
              focusUndo.currentId === selectedTicket.id &&
              selectedTicketFocusState === "current"
            )}
            onFocus={() => focusSelectedTicket(false)}
            onMakeAvailableAndFocus={() => focusSelectedTicket(true)}
            onUndoFocus={undoDrawerFocus}
          />

          <TicketDrawerRelatedContent ready={drawerRelatedState === "ready"}>
            {(ticketActivityError || acceptanceCriteriaError || subtasksError) && (
              <div className="ticket-drawer-load-error" role="alert">
                <p>Some ticket details could not be loaded.</p>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => openTicket(selectedTicket)}
                >
                  Retry Ticket Details
                </button>
              </div>
            )}
            <TicketActivitySection
            items={ticketActivity}
            projects={allProjects}
            loading={ticketActivityLoading}
            error={ticketActivityError}
            expanded={ticketActivityExpanded}
            adding={addingTicketUpdate}
            canAdd={
              !selectedTicketArchived &&
              !addingTicketUpdate &&
              !editingTicket &&
              !editingAcceptanceCriteria &&
              !editingSubtasks &&
              !changingStatus
            }
            draft={newTicketUpdate}
            saving={savingTicketUpdate}
            onStartAdding={startAddingTicketUpdate}
            onDraftChange={setNewTicketUpdate}
            onCancelAdding={cancelAddingTicketUpdate}
            onSave={saveTicketUpdate}
            onToggleExpanded={() =>
              setTicketActivityExpanded((current) => !current)
            }
          />

          <AcceptanceCriteriaSection
            ticket={selectedTicket}
            criteria={progressSessionActive ? editAcceptanceCriteria : acceptanceCriteria}
            editCriteria={editAcceptanceCriteria}
            editing={editingAcceptanceCriteria}
            editingKey={editingCriterionKey}
            loading={acceptanceCriteriaLoading}
            error={acceptanceCriteriaError}
            canEdit={false}
            readOnly={selectedTicketArchived}
            newCriterionText={newCriterionText}
            onStartEditing={startEditingAcceptanceCriteria}
            onNewCriterionTextChange={setNewCriterionText}
            onAddCriterion={addEditAcceptanceCriterion}
            onBeginItemEdit={beginEditAcceptanceCriterion}
            onUpdateItem={updateEditAcceptanceCriterion}
            onCancelItemEdit={cancelEditAcceptanceCriterion}
            onSaveItemEdit={saveEditAcceptanceCriterion}
            onRemoveItem={removeEditAcceptanceCriterion}
            onToggleCompleted={toggleAcceptanceCriterion}
            onCompleteRemaining={completeRemainingAcceptanceCriteria}
            onToggleDeferred={toggleAcceptanceCriterionDeferred}
          />

          <SubtasksSection
            ticket={selectedTicket}
            subtasks={progressSessionActive ? editSubtasks : subtasks}
            editSubtasks={editSubtasks}
            editing={editingSubtasks}
            editingKey={editingSubtaskKey}
            loading={subtasksLoading}
            error={subtasksError || (editingSubtasks ? editTicketError : null)}
            canEdit={false}
            readOnly={selectedTicketArchived}
            onStartEditing={startEditingSubtasks}
            onAddItem={addEditSubtask}
            onBeginItemEdit={beginEditSubtask}
            onUpdateItem={updateEditSubtask}
            onCancelItemEdit={cancelEditSubtask}
            onSaveItemEdit={saveEditSubtask}
            onRemoveItem={removeEditSubtask}
            onToggleCompleted={toggleSubtask}
            onCompleteRemaining={completeRemainingTicketSubtasks}
            onToggleDeferred={toggleSubtaskDeferred}
          />
          <TicketAIReviewSection
            review={aiReview}
            error={aiReviewError}
            options={reviewOptions}
            selectedCriteria={selectedReviewCriteria}
            applying={applyingReview}
            onToggleOption={toggleReviewOption}
            onToggleCriterion={toggleReviewCriterion}
            onDiscard={() => setAIReview(null)}
            onApply={applyAIReview}
          />

            <TicketStatusSection
              open={changingStatus}
              form={statusForm}
              error={statusChangeError}
              onSelectStatus={selectTicketStatus}
              onCancel={cancelChangingStatus}
            />

            <TicketPublicReference ticket={selectedTicket} />

            <TicketProgressReviewPanel
              prompt={progressReviewPrompt}
              review={progressReview}
              loading={progressReviewLoading}
              applying={progressReviewApplying}
              error={progressReviewError}
              selected={selectedProgressSuggestions}
              onStart={() => requestAITransmission(runProgressReview)}
              onToggle={(key) => setSelectedProgressSuggestions((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])}
              onApply={applyProgressReview}
              onDismiss={dismissProgressReview}
            />

            <TicketDrawerActions
              ticketId={selectedTicket.id}
              canChangeStatus={
                !selectedTicketArchived &&
                !changingStatus &&
                !addingTicketUpdate &&
                !aiReview &&
                !aiReviewLoading &&
                editingCriterionKey === null &&
                editingSubtaskKey === null
              }
              canReview={
                !selectedTicketArchived &&
                !editingTicket &&
                !progressSessionActive &&
                !changingStatus &&
                !addingTicketUpdate &&
                selectedTicket?.ai_context_enabled !== false &&
                !projects.some(
                  (project) =>
                    project.id === selectedTicket?.project_id
                    && project.ai_context_enabled === false,
                )
              }
              reviewing={aiReviewLoading}
              hasReviewError={Boolean(aiReviewError)}
              onStartChangingStatus={startChangingStatus}
              onReview={() => requestAITransmission(runAIReview)}
              onCancelReview={cancelAIReview}
            />

          </TicketDrawerRelatedContent>
        </TicketDrawer>
        {stagedCommitSection && (
          <DrawerStagedChangesDialog
            changes={drawerSessionChanges}
            saving={savingTicketEdits}
            note={drawerSessionNote}
            noteRequired={drawerNoteRequired}
            hasDraftUpdate={Boolean(newTicketUpdate.trim())}
            resolutionRequired={finalScopeResolutionRequired}
            resolutionChoice={scopeResolutionChoice}
            currentStatusLabel={currentTicketStatusLabel}
            onResolutionChoice={selectFinalScopeResolution}
            onNoteChange={setDrawerSessionNote}
            onKeepEditing={() => {
              setCloseAfterCommit(false);
              setStagedCommitSection(null);
            }}
            onUndoAll={undoAllDrawerChanges}
            onUndoChange={undoDrawerChange}
            onConfirm={commitDrawerSession}
          />
        )}
      </>)}

      {projectFormMode && (
        <ProjectModal
          mode={projectFormMode}
          form={projectForm}
          error={projectError}
          saving={savingProject}
          starterTicketCount={
            projectFormMode === "create" ? pendingGuidedProjectTickets.length : 0
          }
          onFormChange={setProjectForm}
          onClose={cancelProjectForm}
          onSubmit={saveProject}
        />
      )}

      {creatingTicket && (
        <NewTicketModal
          recovered={newTicketRecovered}
          guidedProgress={guidedTicketReviewProgress}
          review={draftReview}
          onClose={closeNewTicket}
          onSkipGuidedTicket={skipGuidedTicket}
          onEndGuidedReview={finishGuidedTicketReview}
          draftFormProps={{
            projects,
            form: newTicketForm,
            criteria: newTicketCriteria,
            subtasks: newTicketSubtasks,
            criterionInput: newCriterionInput,
            subtaskInput: newSubtaskInput,
            error: newTicketError,
            saving: savingNewTicket,
            reviewing: draftReviewLoading,
            onFormChange: setNewTicketForm,
            onCriterionInputChange: setNewCriterionInput,
            onSubtaskInputChange: setNewSubtaskInput,
            onAddCriterion: addNewTicketCriterion,
            onRemoveCriterion: removeNewTicketCriterion,
            onAddSubtask: addNewTicketSubtask,
            onRemoveSubtask: removeNewTicketSubtask,
            onCancel: closeNewTicket,
            onCreate: () => saveNewTicket(false),
            onReview: () => requestAITransmission(reviewNewTicketDraft),
            onCancelReview: cancelDraftReview,
          }}
          reviewPanelProps={{
            manualCriteria: newTicketCriteria,
            manualSubtasks: newTicketSubtasks,
            reviewOptions: draftReviewOptions,
            selectedCriteria: selectedDraftCriteria,
            selectedSubtasks: selectedDraftSubtasks,
            selectedCriterionRevisions: selectedDraftCriterionRevisions,
            selectedSubtaskRevisions: selectedDraftSubtaskRevisions,
            error: newTicketError,
            saving: savingNewTicket,
            onToggleReviewOption: toggleDraftReviewOption,
            onToggleCriterion: toggleDraftCriterion,
            onToggleSubtask: toggleDraftSubtask,
            onToggleCriterionRevision: toggleDraftCriterionRevision,
            onToggleSubtaskRevision: toggleDraftSubtaskRevision,
            onBack: returnToNewTicketDraft,
            onCreate: () => saveNewTicket(true),
          }}
        />
      )}

      <AITransmissionDisclosure
        open={Boolean(pendingAITransmission)}
        onCancel={cancelAITransmission}
        onContinue={continueAITransmission}
      />
    </div>
  );
}

export default App;
