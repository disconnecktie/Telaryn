// Owns Project Review generation, decisions, focus action, final preview, and apply confirmation.
import { useEffect, useMemo, useRef, useState } from "react";
import AITransmissionDisclosure from "../AITransmissionDisclosure";
import {
  hasRecentAITransmissionAcknowledgment,
  recordAITransmissionAcknowledgment,
} from "../../aiTransmissionAcknowledgment";
import {
  applyProjectReview,
  createProjectReview,
  getProjectReviewApplicationPreview,
  getProjectReviewContext,
  getProjectReviewDecisions,
  makeProjectReviewFocus,
  getProjectReviews,
  saveProjectReviewDecision,
  undoProjectReviewFocus,
} from "../../api";
import { formatLocalDateTime } from "../../time";
import { localTicketReference } from "../../ticketReference";
import "./ProjectReviewPanel.css";

const BASIS_LABELS = {
  supported: "Supported",
  inferred: "Inferred",
  recommended: "Recommended",
};

const FAILURE_MESSAGES = {
  invalid_schema: "Telaryn returned a review that did not match the required structure.",
  invalid_evidence: "Telaryn returned evidence that could not be verified in this project snapshot.",
  invalid_focus: "Telaryn recommended focus outside the active project snapshot.",
  invalid_proposal: "Telaryn returned a proposal that did not meet the approved safety rules.",
  provider_error: "The configured AI provider could not complete the request.",
  provider_timeout: "The AI provider did not respond before the review deadline.",
  invalid_response: "Telaryn could not validate the returned Project Review.",
  concurrent_duplicate: "A matching review completed in another request.",
};



function PrivateTicketExclusions({ tickets }) {
  if (!tickets?.length) return null;

  return (
    <aside className="project-review-private-exclusions" role="status">
      <strong>
        {tickets.length} Private {tickets.length === 1 ? "Ticket was" : "Tickets were"} excluded
      </strong>
      <span>
        Telaryn did not send their content to an AI provider. They may contain
        information that would materially affect this review.
      </span>
      <ul>
        {tickets.map((ticket) => <li key={ticket.id}>{ticket.title}</li>)}
      </ul>
    </aside>
  );
}

const PROPOSAL_LABELS = {
  create_ticket: "Create ticket",
  edit_ticket: "Edit ticket",
  change_ticket_priority: "Change priority",
  add_acceptance_criteria: "Add acceptance criteria",
  add_subtasks: "Add subtasks",
  update_project_context: "Update project context",
  recommend_current_focus: "Recommend current focus",
};


function formatFieldName(value) {
  return value
    .replace(/^project_/, "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function Evidence({ items }) {
  if (!items?.length) return null;
  return (
    <details className="project-review-evidence">
      <summary>Why Telaryn thinks this</summary>
      <ul>
        {items.map((item, index) => (
          <li key={`${item.source_type}-${item.source_id}-${index}`}>
            <span>{formatFieldName(item.source_type)}</span>
            <p>{item.summary}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

function ReviewItem({ item, kind }) {
  return (
    <article className="project-review-item">
      <div className="project-review-item-heading">
        <span>{kind}</span>
        <div>
          <em>{BASIS_LABELS[item.basis] || item.basis}</em>
          {item.significance && <strong>{item.significance}</strong>}
        </div>
      </div>
      <p>{item.summary}</p>
      <Evidence items={item.evidence} />
    </article>
  );
}

function ProposedChanges({ changes }) {
  const entries = Object.entries(changes || {}).filter(([, value]) => {
    if (value === null || value === "") return false;
    return !Array.isArray(value) || value.length > 0;
  });
  if (!entries.length) return null;

  return (
    <dl className="project-review-changes">
      {entries.map(([field, value]) => (
        <div key={field}>
          <dt>{formatFieldName(field)}</dt>
          <dd>
            {Array.isArray(value) ? (
              <ul>{value.map((item) => <li key={item}>{item}</li>)}</ul>
            ) : (
              String(value)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}


const DECISION_LABELS = {
  pending: "Pending",
  approved: "Approved · Not applied",
  rejected: "Rejected",
  deferred: "Deferred",
};

function EditableProposal({ proposal, value, onCancel, onSave, saving }) {
  const [draft, setDraft] = useState(() => structuredClone(value || proposal.proposed_changes));
  const fields = Object.entries(draft).filter(([, fieldValue]) => (
    fieldValue !== null && fieldValue !== "" && (!Array.isArray(fieldValue) || fieldValue.length)
  ));

  function updateField(field, nextValue, originalValue) {
    setDraft((current) => ({
      ...current,
      [field]: Array.isArray(originalValue)
        ? nextValue.split("\n").map((item) => item.trim()).filter(Boolean)
        : nextValue,
    }));
  }

  return (
    <div className="project-review-editor">
      <p>Edit the candidate only. Telaryn’s original proposal remains unchanged.</p>
      {fields.map(([field, fieldValue]) => (
        <label key={field}>
          <span>{formatFieldName(field)}</span>
          {field === "priority" || field === "ticket_type" ? (
            <select
              value={fieldValue}
              onChange={(event) => updateField(field, event.target.value, fieldValue)}
            >
              {(field === "priority"
                ? ["low", "medium", "high", "critical"]
                : ["task", "problem", "request", "research", "development"]
              ).map((option) => <option key={option} value={option}>{formatFieldName(option)}</option>)}
            </select>
          ) : (
            <textarea
              rows={Array.isArray(fieldValue) ? 3 : 2}
              value={Array.isArray(fieldValue) ? fieldValue.join("\n") : fieldValue}
              onChange={(event) => updateField(field, event.target.value, fieldValue)}
            />
          )}
        </label>
      ))}
      <div>
        <button type="button" disabled={saving} onClick={() => onSave(draft)}>Save candidate</button>
        <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function ProjectReviewPanel({ project, tickets, onOpenTicket }) {
  const [attempts, setAttempts] = useState([]);
  const [snapshotVersion, setSnapshotVersion] = useState(null);
  const [selectedReviewId, setSelectedReviewId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [decisions, setDecisions] = useState({});
  const [decisionSaving, setDecisionSaving] = useState(null);
  const [editingProposal, setEditingProposal] = useState(null);
  const [undoDecision, setUndoDecision] = useState(null);
  const [startingReview, setStartingReview] = useState(false);
  const [applicationPreview, setApplicationPreview] = useState(null);
  const [applying, setApplying] = useState(false);
  const [disclosureOpen, setDisclosureOpen] = useState(false);
  const startTimer = useRef(null);

  useEffect(() => {
    let active = true;

    Promise.all([
      getProjectReviews(project.id),
      getProjectReviewContext(project.id),
    ])
      .then(([reviewAttempts, context]) => {
        if (!active) return;
        setAttempts(reviewAttempts);
        setSnapshotVersion(context.snapshot_version);
      })
      .catch((loadError) => {
        if (active) setError(loadError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      window.clearTimeout(startTimer.current);
    };
  }, [project.id]);

  const hasActiveReview = attempts.some((attempt) => (
    attempt.status === "pending" || attempt.status === "running"
  ));

  useEffect(() => {
    if (!hasActiveReview) return undefined;
    let active = true;
    const refresh = async () => {
      try {
        const refreshed = await getProjectReviews(project.id);
        if (active) setAttempts(refreshed);
      } catch {
        // Keep the existing status visible until the next polling attempt.
      }
    };
    const interval = window.setInterval(refresh, 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [hasActiveReview, project.id]);

  const completedReviews = useMemo(
    () => attempts.filter((attempt) => attempt.status === "completed" && attempt.result),
    [attempts],
  );
  const selectedReview =
    completedReviews.find((attempt) => attempt.id === selectedReviewId) ||
    completedReviews[0] ||
    null;
  const latestAttempt = attempts[0] || null;
  const excludedPrivateTickets = (
    selectedReview?.excluded_private_tickets
    || latestAttempt?.excluded_private_tickets
    || []
  );
  const isCurrent = Boolean(
    selectedReview && snapshotVersion === selectedReview.snapshot_version,
  );
  useEffect(() => {
    let active = true;
    if (!selectedReview) {
      return () => { active = false; };
    }
    getProjectReviewDecisions(project.id, selectedReview.id)
      .then((items) => {
        if (active) {
          setDecisions(Object.fromEntries(items.map((item) => [item.proposal_index, item])));
        }
      })
      .catch((decisionError) => {
        if (active) setError(decisionError.message);
      });
    return () => { active = false; };
  }, [project.id, selectedReview]);

  const ticketById = useMemo(
    () => new Map(tickets.map((ticket) => [ticket.id, ticket])),
    [tickets],
  );

  function generateReview() {
    if (hasRecentAITransmissionAcknowledgment()) {
      prepareReview();
      return;
    }
    setDisclosureOpen(true);
  }

  function confirmReviewTransmission() {
    recordAITransmissionAcknowledgment();
    setDisclosureOpen(false);
    prepareReview();
  }

  function prepareReview() {
    const forceFresh = Boolean(isCurrent && selectedReview);
    if (forceFresh) {
      const completedAt = formatLocalDateTime(selectedReview.completed_at);
      const confirmed = window.confirm(
        `Telaryn already completed a review of this unchanged project on ${completedAt}. Run a new review anyway?`,
      );
      if (!confirmed) return;
    }

    setStartingReview(true);
    setError(null);
    setNotice("Review starts in 2 seconds. Undo now if this was accidental.");
    startTimer.current = window.setTimeout(() => runReview(forceFresh), 2000);
  }

  function undoReviewStart() {
    window.clearTimeout(startTimer.current);
    startTimer.current = null;
    setStartingReview(false);
    setNotice("Project Review was not started.");
  }

  async function runReview(forceFresh = false) {
    setStartingReview(false);
    setGenerating(true);
    setError(null);
    setNotice(null);
    const knownAttemptIds = new Set(attempts.map((attempt) => attempt.id));
    try {
      const review = await createProjectReview(project.id, { forceFresh });
      setAttempts((current) => [
        review,
        ...current.filter((attempt) => attempt.id !== review.id),
      ]);
      setSnapshotVersion(review.snapshot_version);
      setSelectedReviewId(review.id);
      setExpanded(true);
      if (knownAttemptIds.has(review.id) && review.status === "completed") {
        setNotice(
          `Nothing in this project has changed since the review from ${formatLocalDateTime(review.completed_at)}. Telaryn reused that current review instead of making another AI request.`,
        );
      } else if (review.status === "pending" || review.status === "running") {
        setNotice("Telaryn queued a full review of the current snapshot. You can leave this page while it runs.");
      } else {
        setNotice("Telaryn completed a new review of the current project snapshot.");
      }
    } catch (reviewError) {
      setError(reviewError.message);
      try {
        setAttempts(await getProjectReviews(project.id));
      } catch {
        // Preserve the actionable generation error when history refresh also fails.
      }
    } finally {
      setGenerating(false);
    }
  }

  async function updateDecision(index, next, editedChanges = undefined, recordUndo = true) {
    const previous = decisions[index] || {
      proposal_index: index,
      decision: "pending",
      edited_changes: null,
      note: null,
    };
    setDecisionSaving(index);
    setError(null);
    try {
      const saved = await saveProjectReviewDecision(
        project.id,
        selectedReview.id,
        index,
        {
          decision: next,
          edited_changes: editedChanges === undefined ? previous.edited_changes : editedChanges,
          note: previous.note,
        },
      );
      setDecisions((current) => ({ ...current, [index]: saved }));
      setEditingProposal(null);
      if (recordUndo) setUndoDecision({ index, previous });
    } catch (decisionError) {
      setError(decisionError.message);
    } finally {
      setDecisionSaving(null);
    }
  }

  async function undoLastDecision() {
    if (!undoDecision) return;
    const { index, previous } = undoDecision;
    setUndoDecision(null);
    await updateDecision(index, previous.decision, previous.edited_changes, false);
    setUndoDecision(null);
  }

  async function setRecommendedFocus(index) {
    setDecisionSaving(index);
    setError(null);
    try {
      const saved = await makeProjectReviewFocus(
        project.id, selectedReview.id, index,
      );
      setDecisions((current) => ({ ...current, [index]: saved }));
      setNotice("Current Focus changed. Ticket status was unchanged.");
    } catch (focusError) {
      setError(focusError.message);
    } finally {
      setDecisionSaving(null);
    }
  }

  async function undoRecommendedFocus(index) {
    setDecisionSaving(index);
    setError(null);
    try {
      const saved = await undoProjectReviewFocus(
        project.id, selectedReview.id, index,
      );
      setDecisions((current) => ({ ...current, [index]: saved }));
      setNotice("Previous Current Focus restored.");
    } catch (focusError) {
      setError(focusError.message);
    } finally {
      setDecisionSaving(null);
    }
  }

  async function openApplicationPreview() {
    setError(null);
    try {
      setApplicationPreview(
        await getProjectReviewApplicationPreview(project.id, selectedReview.id),
      );
    } catch (previewError) {
      setError(previewError.message);
    }
  }

  async function applyApprovedChanges() {
    setApplying(true);
    setError(null);
    try {
      const application = await applyProjectReview(project.id, selectedReview.id);
      const refreshed = await getProjectReviewDecisions(project.id, selectedReview.id);
      setDecisions(Object.fromEntries(refreshed.map((item) => [item.proposal_index, item])));
      setApplicationPreview(null);
      const label = application.proposal_indexes.length === 1 ? "change" : "changes";
      setNotice(
        "Applied " + application.proposal_indexes.length + " approved " + label +
        " atomically. Ticket status and Current Focus were unchanged.",
      );
    } catch (applyError) {
      setError(applyError.message);
    } finally {
      setApplying(false);
    }
  }

  function openTicket(ticketId) {
    const ticket = ticketById.get(ticketId);
    if (ticket) onOpenTicket(ticket);
  }

  if (loading) {
    return (
      <section className="project-review-shell" aria-busy="true">
        <p className="eyebrow">TELARYN PROJECT REVIEW</p>
        <p className="muted">Checking for an existing review…</p>
      </section>
    );
  }

  if (project.ai_context_enabled === false) {
    return (
      <section className="project-review-shell">
        <div className="project-review-intro">
          <div>
            <p className="eyebrow">TELARYN PROJECT REVIEW</p>
            <h2>Project Review is unavailable for this Private project.</h2>
            <p>
              Telaryn will not send this project’s content to an AI provider.
              Changing this setting does not change workspace access.
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (!selectedReview) {
    return (
      <section className="project-review-shell">
        <div className="project-review-intro">
          <div>
            <p className="eyebrow">TELARYN PROJECT REVIEW</p>
            <h2>Step back and review the whole project.</h2>
            <p>
              Telaryn can examine project health and planning, then propose
              improvements without changing any project or ticket. Start a review
              when the project has enough real work to benefit from a wider view.
            </p>
          </div>
          <button
            className="secondary-button"
            type="button"
            disabled={generating || startingReview || hasActiveReview}
            onClick={generateReview}
          >
            {startingReview ? "Starting…" : hasActiveReview ? "Review Queued" : generating ? "Queueing Review…" : "Review Project with Telaryn"}
          </button>
        </div>
        <PrivateTicketExclusions tickets={excludedPrivateTickets} />
        {startingReview && (
          <div className="project-review-running" role="status">
            <span>Telaryn has not sent anything yet.</span>
            <button type="button" onClick={undoReviewStart}>Undo</button>
          </div>
        )}
        {hasActiveReview && (
          <div className="project-review-running" role="status">
            <span>
              {latestAttempt?.status === "pending"
                ? "Telaryn queued this full project review."
                : "Telaryn is reviewing the full project snapshot."} You can leave this page.
            </span>
          </div>
        )}
        {latestAttempt && latestAttempt.status !== "completed" && !hasActiveReview && !generating && (
          <p className="project-review-attempt-note">
            {FAILURE_MESSAGES[latestAttempt.safe_error_category] ||
              "The latest attempt did not complete."}{" "}
            Your project was not changed.
          </p>
        )}
        {error && <p className="project-review-error" role="alert">{error}</p>}
        <AITransmissionDisclosure
          open={disclosureOpen}
          onCancel={() => setDisclosureOpen(false)}
          onContinue={confirmReviewTransmission}
        />
      </section>
    );
  }

  const result = selectedReview.result;
  const focusTicket = result.recommended_focus
    ? ticketById.get(result.recommended_focus.ticket_id)
    : null;

  return (
    <section className="project-review-shell">
      <div className="project-review-intro">
        <div>
          <p className="eyebrow">TELARYN PROJECT REVIEW</p>
          <div className="project-review-title-row">
            <h2>{expanded ? "Project Review" : "Telaryn Project Review"}</h2>
            <span className={isCurrent ? "current" : "stale"}>
              {isCurrent ? "Current snapshot" : "Project changed"}
            </span>
          </div>
          {!expanded && (
            <>
              <p className="project-review-compact-summary">{result.summary}</p>
              <p>
                {result.findings.length} findings · {result.risks.length} risks ·{" "}
                {result.proposals.length} proposals
              </p>
            </>
          )}
        </div>
        <div className="project-review-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Close Full Review" : "Open Full Review"}
          </button>
          <button
            className="project-review-text-action"
            type="button"
            disabled={generating || startingReview || hasActiveReview}
            onClick={generateReview}
          >
            {startingReview ? "Starting…" : hasActiveReview ? "Review Queued" : generating ? "Queueing…" : "Review Again"}
          </button>
        </div>
      </div>

      {startingReview && (
        <div className="project-review-running" role="status">
          <span>Telaryn has not sent anything yet.</span>
          <button type="button" onClick={undoReviewStart}>Undo</button>
        </div>
      )}
      {hasActiveReview && (
        <div className="project-review-running" role="status">
          <span>
            {latestAttempt?.status === "pending"
              ? "Telaryn queued this full project review."
              : "Telaryn is reviewing the full project snapshot."} You can leave this page.
          </span>
        </div>
      )}
      {notice && <p className="project-review-notice" role="status">{notice}</p>}
      {error && <p className="project-review-error" role="alert">{error}</p>}

      {expanded && (
        <div className="project-review-content">
          <div className="project-review-summary">
            <div className="project-review-summary-heading">
              <span>OVERALL ASSESSMENT</span>
              <small>Reviewed {formatLocalDateTime(selectedReview.completed_at)}</small>
            </div>
            <p>{result.summary}</p>
          </div>

          {result.recommended_focus && (
            <article className="project-review-focus">
              <span>RECOMMENDED CURRENT FOCUS</span>
              <h3>{focusTicket?.title || "Referenced Ticket"}</h3>
              <p>{result.recommended_focus.rationale}</p>
              <Evidence items={result.recommended_focus.evidence} />
              {focusTicket && (
                <button type="button" onClick={() => openTicket(focusTicket.id)}>
                  Open Ticket
                </button>
              )}
            </article>
          )}

          {(result.findings.length > 0 || result.risks.length > 0) && (
            <div className="project-review-grid">
              <div>
                <h3>Findings</h3>
                {result.findings.length ? result.findings.map((item, index) => (
                  <ReviewItem key={index} item={item} kind="Finding" />
                )) : <p className="muted">No material findings.</p>}
              </div>
              <div>
                <h3>Risks</h3>
                {result.risks.length ? result.risks.map((item, index) => (
                  <ReviewItem key={index} item={item} kind="Risk" />
                )) : <p className="muted">No material risks.</p>}
              </div>
            </div>
          )}

          {result.planning_guidance.length > 0 && (
            <div className="project-review-section">
              <h3>Planning guidance</h3>
              <div className="project-review-list">
                {result.planning_guidance.map((item, index) => (
                  <ReviewItem key={index} item={item} kind="Guidance" />
                ))}
              </div>
            </div>
          )}

          <div className="project-review-section">
            <div className="project-review-section-heading">
              <div>
                <h3>Proposed changes</h3>
                <p>Telaryn has not changed your project.</p>
              </div>
              <span>{result.proposals.length}</span>
            </div>
            {result.proposals.length ? (
              <div className="project-review-list">
                {result.proposals.map((proposal, index) => {
                  const targetTicket = proposal.target_ticket_id
                    ? ticketById.get(proposal.target_ticket_id)
                    : null;
                  return (
                    <article className="project-review-proposal" key={index}>
                      <div className="project-review-item-heading">
                        <span>{PROPOSAL_LABELS[proposal.proposal_type] || formatFieldName(proposal.proposal_type)}</span>
                        <strong>{proposal.significance}</strong>
                      </div>
                      <h4>{proposal.summary}</h4>
                      {targetTicket && (
                        <button type="button" onClick={() => openTicket(targetTicket.id)}>
                          {localTicketReference(targetTicket)} {targetTicket.title}
                        </button>
                      )}
                      <ProposedChanges
                        changes={decisions[index]?.edited_changes || proposal.proposed_changes}
                      />
                      <Evidence items={proposal.evidence} />
                      <div className="project-review-decision">
                        <strong>
                          {decisions[index]?.application_id
                            ? "Applied"
                            : decisions[index]?.focus_applied_at
                              ? "Focus set"
                              : DECISION_LABELS[decisions[index]?.decision || "pending"]}
                          {undoDecision?.index === index && (
                            <button
                              className="project-review-inline-undo"
                              type="button"
                              onClick={undoLastDecision}
                            >
                              Undo
                            </button>
                          )}
                        </strong>
                        {decisions[index]?.application_id ? (
                          <span>Recorded in atomic application #{decisions[index].application_id}.</span>
                        ) : decisions[index]?.focus_applied_at ? (
                          <div>
                            <span className="project-review-focus-state">Current Focus updated</span>
                            <button
                              type="button"
                              disabled={decisionSaving === index}
                              onClick={() => undoRecommendedFocus(index)}
                            >
                              Undo
                            </button>
                          </div>
                        ) : !isCurrent ? (
                          <span>Review Again to make decisions on current project data.</span>
                        ) : proposal.proposal_type === "recommend_current_focus" ? (
                          <div>
                            <button
                              type="button"
                              disabled={decisionSaving === index}
                              onClick={() => setRecommendedFocus(index)}
                            >
                              Make Focus
                            </button>
                            {["rejected", "deferred"].map((decision) => (
                              <button
                                key={decision}
                                type="button"
                                disabled={
                                  decisionSaving === index ||
                                  decisions[index]?.decision === decision
                                }
                                aria-pressed={decisions[index]?.decision === decision}
                                onClick={() => updateDecision(index, decision)}
                              >
                                {decision === "rejected" ? "Reject" : "Defer"}
                              </button>
                            ))}
                          </div>
                        ) : (
                          <div>
                            {["approved", "rejected", "deferred"].map((decision) => (
                              <button
                                key={decision}
                                type="button"
                                disabled={
                                  decisionSaving === index ||
                                  decisions[index]?.decision === decision
                                }
                                aria-pressed={decisions[index]?.decision === decision}
                                onClick={() => updateDecision(index, decision)}
                              >
                                {decision === "approved" ? "Approve" : decision === "rejected" ? "Reject" : "Defer"}
                              </button>
                            ))}
                            {decisions[index]?.decision === "approved" &&
                              proposal.proposal_type !== "recommend_current_focus" && (
                              <button type="button" onClick={() => setEditingProposal(index)}>
                                Edit candidate
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                      {editingProposal === index && (
                        <EditableProposal
                          proposal={proposal}
                          value={decisions[index]?.edited_changes}
                          saving={decisionSaving === index}
                          onCancel={() => setEditingProposal(null)}
                          onSave={(changes) => updateDecision(index, "approved", changes)}
                        />
                      )}
                    </article>
                  );
                })}
              </div>
            ) : (
              <p className="muted">Telaryn did not identify a necessary project change.</p>
            )}
            <div className="project-review-application">
              <div>
                <strong>Ready to apply</strong>
                <span>
                  {Object.values(decisions).filter(
                    (decision) =>
                      decision.decision === "approved" &&
                      !decision.application_id &&
                      result.proposals[decision.proposal_index]?.proposal_type !==
                        "recommend_current_focus",
                  ).length} approved, unapplied
                </span>
              </div>
              <button
                type="button"
                disabled={
                  !isCurrent ||
                  !Object.values(decisions).some(
                    (decision) =>
                      decision.decision === "approved" &&
                      !decision.application_id &&
                      result.proposals[decision.proposal_index]?.proposal_type !==
                        "recommend_current_focus",
                  )
                }
                onClick={openApplicationPreview}
              >
                Review Approved Changes
              </button>
            </div>
            {applicationPreview && (
              <div className="project-review-application-preview">
                <div className="project-review-section-heading">
                  <div>
                    <h3>Final approved-change summary</h3>
                    <p>This is the exact batch Telaryn will commit. There is no post-application Undo.</p>
                  </div>
                  <span>{applicationPreview.items.length}</span>
                </div>
                {applicationPreview.items.map((item) => (
                  <article key={item.proposal_index}>
                    <strong>{item.summary}</strong>
                    <ProposedChanges changes={item.candidate_changes} />
                  </article>
                ))}
                {applicationPreview.conflicts.length > 0 && (
                  <div className="project-review-conflicts" role="alert">
                    <strong>Resolve these conflicts first</strong>
                    <ul>{applicationPreview.conflicts.map((conflict) => <li key={conflict}>{conflict}</li>)}</ul>
                  </div>
                )}
                <div className="project-review-application-actions">
                  <button type="button" onClick={() => setApplicationPreview(null)}>Back</button>
                  <button
                    type="button"
                    disabled={!applicationPreview.can_apply || applying}
                    onClick={applyApprovedChanges}
                  >
                    {applying
                      ? "Applying…"
                      : "Apply " + applicationPreview.items.length + " Approved " +
                        (applicationPreview.items.length === 1 ? "Change" : "Changes")}
                  </button>
                </div>
              </div>
            )}
            <p className="project-review-advisory">
              Approval alone changes nothing. Project and Ticket changes use the reviewed atomic application above; Current Focus recommendations use their separate Make Focus action.
            </p>
          </div>

          <div className="project-review-history">
            <button
              type="button"
              aria-expanded={historyOpen}
              onClick={() => setHistoryOpen((value) => !value)}
            >
              Review History <span>{attempts.length}</span>
            </button>
            {historyOpen && (
              <ul>
                {attempts.map((attempt) => (
                  <li key={attempt.id}>
                    <div>
                      <strong>{attempt.status === "completed" ? "Completed" : "Did not complete"}</strong>
                      <span>{formatLocalDateTime(attempt.completed_at || attempt.created_at)}</span>
                    </div>
                    {attempt.status === "completed" && attempt.result && (
                      <button
                        type="button"
                        aria-pressed={attempt.id === selectedReview.id}
                        onClick={() => setSelectedReviewId(attempt.id)}
                      >
                        {attempt.id === selectedReview.id ? "Viewing" : "View"}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      <AITransmissionDisclosure
        open={disclosureOpen}
        onCancel={() => setDisclosureOpen(false)}
        onContinue={confirmReviewTransmission}
      />
    </section>
  );
}

export default ProjectReviewPanel;
