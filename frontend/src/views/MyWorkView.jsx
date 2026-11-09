// Presents one chosen focus, three suggestions, and intentional upcoming work.
import { useCallback, useEffect, useRef, useState } from "react";
import "./MyWorkView.css";
import AITransmissionDisclosure from "../components/AITransmissionDisclosure";
import { SuggestionBasisBadge, SuggestionBasisLegend } from "../components/SuggestionBasis";
import AtlasReviewProgress from "../components/tickets/AtlasReviewProgress";
import {
  hasRecentAITransmissionAcknowledgment,
  recordAITransmissionAcknowledgment,
} from "../aiTransmissionAcknowledgment";
import { localTicketReference } from "../ticketReference";
import { DEFAULT_MY_WORK_SECTION, MY_WORK_SECTIONS } from "../myWorkSections";

function formatLabel(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const proposalItemText = (item) => (typeof item === "string" ? item : item?.text || "");

const TECHNICAL_TOKEN_PATTERN = /([A-Za-z0-9]+(?:[_./@-][A-Za-z0-9]+){2,})/g;
const TECHNICAL_TOKEN = /^[A-Za-z0-9]+(?:[_./@-][A-Za-z0-9]+){2,}$/;
const TECHNICAL_DELIMITER = /^[_./@-]$/;

function BreakableTechnicalText({ children }) {
  return String(children).split(TECHNICAL_TOKEN_PATTERN).map((part, partIndex) => {
    if (!TECHNICAL_TOKEN.test(part)) return part;
    return (
      <code className="my-work-technical-token" key={`${part}-${partIndex}`}>
        {part.split(/([_./@-])/).map((segment, segmentIndex) => (
          TECHNICAL_DELIMITER.test(segment)
            ? <span key={`${segment}-${segmentIndex}`}>{segment}<wbr /></span>
            : segment
        ))}
      </code>
    );
  });
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function localDate(offsetDays = 0) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  return [
    value.getFullYear(),
    String(value.getMonth() + 1).padStart(2, "0"),
    String(value.getDate()).padStart(2, "0"),
  ].join("-");
}

function nextSaturday() {
  const value = new Date();
  const days = (6 - value.getDay() + 7) % 7 || 7;
  return localDate(days);
}

function ProgressLabel({ label, progress }) {
  if (!progress.total) return null;
  return <span>{progress.completed}/{progress.total} {label}</span>;
}

function TicketContext({ item }) {
  return (
    <>
      <div className="my-work-item-topline">
        <span>{localTicketReference(item)}</span>
        <span>{item.project_name || "No project"}</span>
      </div>
      <div className="my-work-item-heading">
        <h3>{item.title}</h3>
        <div className="ticket-inline-status">
          <span className={`priority ${item.priority}`}>{item.priority}</span>
          <span className="status-divider">•</span>
          <span className={`ticket-status ${item.status}`}>{formatLabel(item.status)}</span>
        </div>
      </div>
      <div className="my-work-reasons">
        {item.reasons.map((reason) => <span key={reason}>{reason}</span>)}
      </div>
      {(item.acceptance_criteria.total > 0 || item.subtasks.total > 0) && (
        <div className="my-work-progress">
          <ProgressLabel label="criteria" progress={item.acceptance_criteria} />
          <ProgressLabel label="subtasks" progress={item.subtasks} />
        </div>
      )}
    </>
  );
}

function AvailabilityEditor({ item, onApply, onCancel }) {
  const [choice, setChoice] = useState("tomorrow");
  const [customDate, setCustomDate] = useState(localDate(1));

  function apply() {
    if (choice === "tomorrow") onApply(item, "date", localDate(1));
    else if (choice === "weekend") onApply(item, "date", nextSaturday());
    else if (choice === "custom") onApply(item, "date", customDate);
    else onApply(item, choice, null);
  }

  return (
    <div className="my-work-availability-editor">
      <label>
        <span>Available for Focus</span>
        <select value={choice} onChange={(event) => setChoice(event.target.value)}>
          <option value="tomorrow">Tomorrow</option>
          <option value="weekend">This weekend</option>
          <option value="custom">Choose a date</option>
          <option value="context_change">When something changes</option>
          <option value="manual">Until I restore it</option>
        </select>
      </label>
      {choice === "custom" && (
        <input
          aria-label="Available for Focus date"
          type="date"
          min={localDate()}
          value={customDate}
          onChange={(event) => setCustomDate(event.target.value)}
        />
      )}
      <div>
        <button type="button" className="secondary-button" onClick={onCancel}>Cancel</button>
        <button
          type="button"
          className="ai-button"
          onClick={apply}
          disabled={choice === "custom" && !customDate}
        >
          Set Availability
        </button>
      </div>
    </div>
  );
}

function SuggestionCard({ item, onFocus, onOpenTicket, onSetAvailability }) {
  const [editingAvailability, setEditingAvailability] = useState(false);
  return (
    <article className="my-work-item my-work-suggestion">
      <div className="my-work-suggestion-copy">
        <TicketContext item={item} />
        <p className="my-work-suggestion-next">
          <span>Next</span>
          {item.next_action?.title || "A concrete next action needs to be defined"}
        </p>
      </div>
      <div className="my-work-card-actions">
        <button type="button" className="ai-button" onClick={() => onFocus(item)}>Focus This</button>
        <button type="button" className="secondary-button" onClick={() => setEditingAvailability(true)}>Not Now</button>
        <button type="button" className="text-button" onClick={() => onOpenTicket(item)}>Open</button>
      </div>
      {editingAvailability && (
        <AvailabilityEditor
          item={item}
          onApply={(ticket, mode, availableOn) => {
            onSetAvailability(ticket, mode, availableOn);
            setEditingAvailability(false);
          }}
          onCancel={() => setEditingAvailability(false)}
        />
      )}
    </article>
  );
}

function WorkIntakeProposal({
  proposal, sourceText, answers, refinementCount, refining,
  onAnswerChange, onRefine, onCancelRefinement, onEditRequest, onDiscard, onContinue,
}) {
  const targetTicket = proposal.matched_tickets?.find(
    (item) => item.id === proposal.target_ticket_id
  );
  const targetProject = proposal.matched_projects?.find(
    (item) => item.id === proposal.target_project_id
  );
  const canContinue = proposal.action !== "needs_clarification";
  const proposedStructure = [
    ...(proposal.proposed_tickets || []).flatMap((ticket) => [
      ...(ticket.acceptance_criteria || []),
      ...(ticket.subtasks || []),
    ]),
    ...(proposal.proposed_ticket_changes?.acceptance_criteria || []),
    ...(proposal.proposed_ticket_changes?.subtasks || []),
  ];
  const hasSuggestionBasis = proposedStructure.some(
    (item) => typeof item === "object" && item?.basis
  );

  return (
    <div className="work-intake-proposal" aria-live="polite">
      <div className="work-intake-proposal-heading">
        <div>
          <p className="eyebrow">TELARYN PROPOSAL</p>
          <h3>{proposal.summary}</h3>
        </div>
        <span className={`work-intake-confidence ${proposal.confidence}`}>
          {proposal.confidence} confidence
        </span>
      </div>
      <p>{proposal.rationale}</p>
      {hasSuggestionBasis && <SuggestionBasisLegend />}

      {targetProject && (
        <div className="work-intake-match">
          <span>Suggested Project</span>
          <strong>{targetProject.reference} · {targetProject.name}</strong>
        </div>
      )}
      {targetTicket && (
        <div className="work-intake-match">
          <span>Existing Ticket</span>
          <strong>{targetTicket.reference} · {targetTicket.title}</strong>
        </div>
      )}
      {proposal.proposed_project && (
        <div className="work-intake-proposed-item">
          <span>Proposed Project</span>
          <strong>{proposal.proposed_project.name}</strong>
          {proposal.proposed_project.purpose && <p>{proposal.proposed_project.purpose}</p>}
        </div>
      )}
      {proposal.proposed_tickets?.length > 0 && (
        <div className="work-intake-proposed-list">
          <span>{proposal.proposed_tickets.length === 1 ? "Proposed Ticket" : "Proposed Tickets"}</span>
          {proposal.proposed_tickets.map((ticket, index) => (
            <article key={`${ticket.title}-${index}`}>
              <strong>{ticket.title}</strong>
              {ticket.description && <p>{ticket.description}</p>}
              <details className="work-intake-ticket-structure">
                <summary>
                  <span>
                    <strong>Proposed plan</strong>
                    <small>
                      {ticket.acceptance_criteria.length}{" "}
                      {ticket.acceptance_criteria.length === 1 ? "outcome" : "outcomes"}
                      {" · "}
                      {ticket.subtasks.length}{" "}
                      {ticket.subtasks.length === 1 ? "step" : "steps"}
                    </small>
                  </span>
                </summary>
                <div className="work-intake-plan">
                  <section className="work-intake-plan-section outcomes">
                    <header>
                      <span aria-hidden="true">1</span>
                      <div>
                        <strong>Done looks like</strong>
                        <small>Acceptance criteria</small>
                      </div>
                    </header>
                    <ol>
                      {ticket.acceptance_criteria.map((criterion, itemIndex) => (
                        <li key={`${proposalItemText(criterion)}-${itemIndex}`}>
                          <span className="work-intake-item-number" aria-hidden="true">
                            {itemIndex + 1}
                          </span>
                          <div>
                            <span>{proposalItemText(criterion)}</span>
                            <SuggestionBasisBadge basis={criterion?.basis} />
                          </div>
                        </li>
                      ))}
                    </ol>
                  </section>
                  <section className="work-intake-plan-section steps">
                    <header>
                      <span aria-hidden="true">2</span>
                      <div>
                        <strong>Steps to take</strong>
                        <small>Subtasks</small>
                      </div>
                    </header>
                    <ol>
                      {ticket.subtasks.map((subtask, itemIndex) => (
                        <li key={`${proposalItemText(subtask)}-${itemIndex}`}>
                          <span className="work-intake-item-number" aria-hidden="true">
                            {itemIndex + 1}
                          </span>
                          <div>
                            <span>{proposalItemText(subtask)}</span>
                            <SuggestionBasisBadge basis={subtask?.basis} />
                          </div>
                        </li>
                      ))}
                    </ol>
                  </section>
                </div>
              </details>
              {proposal.action === "create_tickets" && (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => onContinue(sourceText, proposal, index)}
                >
                  Review This Ticket
                </button>
              )}
            </article>
          ))}
        </div>
      )}
      {proposal.proposed_ticket_changes && (
        <div className="work-intake-proposed-item">
          <span>Proposed additions or changes</span>
          {proposal.proposed_ticket_changes.title && <strong>{proposal.proposed_ticket_changes.title}</strong>}
          {proposal.proposed_ticket_changes.acceptance_criteria?.length > 0 && (
            <ul>
              {proposal.proposed_ticket_changes.acceptance_criteria.map((item, index) => (
                <li key={`criterion-${index}`}>
                  <SuggestionBasisBadge basis={item?.basis} />
                  <span>{proposalItemText(item)}</span>
                </li>
              ))}
            </ul>
          )}
          {proposal.proposed_ticket_changes.subtasks?.length > 0 && (
            <ul>
              {proposal.proposed_ticket_changes.subtasks.map((item, index) => (
                <li key={`subtask-${index}`}>
                  <SuggestionBasisBadge basis={item?.basis} />
                  <span>{proposalItemText(item)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {proposal.is_provisional && (
        <div className="work-intake-provisional" role="status">
          <strong>Built from the context available</strong>
          <p>{proposal.clarification_prompt || "Answering a few focused questions can make this proposal more specific and actionable."}</p>
        </div>
      )}
      {proposal.questions?.length > 0 && (refinementCount < 1 || refining) && (
        <div className="work-intake-questions">
          <span>Improve this proposal</span>
          <p>Answer what you can, or continue with Telaryn’s current proposal.</p>
          <div className="work-intake-question-list">
            {proposal.questions.map((question, index) => (
              <label key={question}>
                <span>{question}</span>
                <textarea
                  rows="2"
                  maxLength="2000"
                  value={answers[index] || ""}
                  onChange={(event) => onAnswerChange(index, event.target.value)}
                  disabled={refining}
                />
              </label>
            ))}
          </div>
          {refining ? (
            <AtlasReviewProgress
              onCancel={onCancelRefinement}
              label="Telaryn is refining this proposal with your answers"
              cancelLabel="Cancel Refinement"
              compact
            />
          ) : (
            <button type="button" className="secondary-button" onClick={onRefine}
              disabled={!answers.some((answer) => answer.trim())}>
              Refine Proposal
            </button>
          )}
        </div>
      )}

      <div className="my-work-guided-intake-actions">
        <span>Nothing has been created or changed.</span>
        <div>
          <button type="button" className="text-button" onClick={onDiscard} disabled={refining}>Discard</button>
          <button type="button" className="secondary-button" onClick={onEditRequest} disabled={refining}>Edit Request</button>
          {canContinue && proposal.action !== "create_tickets" && (
            <button type="button" className="ai-button" disabled={refining} onClick={() => onContinue(sourceText, proposal, 0)}>
              {proposal.is_provisional
                ? "Continue with Current Proposal"
                : proposal.action === "create_project"
                ? "Continue to Project Draft"
                : proposal.action === "create_ticket"
                  ? "Continue to Ticket Draft"
                  : "Open Existing Ticket"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const WORK_INTAKE_FAILURE_MESSAGES = {
  provider_timeout: "Telaryn did not finish shaping this work in time. Nothing was changed.",
  provider_error: "The configured AI provider could not shape this work right now. Nothing was changed.",
  invalid_response: "Telaryn received a proposal it could not safely validate. Nothing was changed.",
  unexpected_failure: "Telaryn could not finish shaping this work. Nothing was changed.",
  cancelled: "Work Intake was cancelled. Nothing was changed.",
};

const GUIDED_WORK_EXAMPLE = "Plan a small community volunteer event for late October. I need to choose a venue, confirm a budget, recruit five volunteers, publish registration, and have a clear go/no-go decision two weeks before the event.";

function GuidedWorkIntake({
  onStart,
  onRefine,
  onRecover,
  onGet,
  onCancel,
  onDismiss,
  onContinue,
  prominent = false,
  sectionProps = {},
}) {
  const [expanded, setExpanded] = useState(prominent);
  const [sourceText, setSourceText] = useState("");
  const [attempt, setAttempt] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [disclosureOpen, setDisclosureOpen] = useState(false);
  const [clarificationAnswers, setClarificationAnswers] = useState([]);
  const intakeAbortController = useRef(null);

  const updateFromAttempt = useCallback((nextAttempt) => {
    if (!nextAttempt) return;
    setAttempt(nextAttempt);
    setSourceText(nextAttempt.source_text || "");
    setClarificationAnswers(nextAttempt.clarification_answers || []);
    if (nextAttempt.status === "completed" && nextAttempt.result) {
      setProposal(nextAttempt.result);
      setSubmitting(false);
      setError(null);
      return;
    }
    if (nextAttempt.status === "pending" || nextAttempt.status === "running") {
      if (nextAttempt.result) setProposal(nextAttempt.result);
      setSubmitting(true);
      setError(null);
      return;
    }
    setProposal(nextAttempt.result || null);
    setSubmitting(false);
    setError(
      WORK_INTAKE_FAILURE_MESSAGES[nextAttempt.safe_error_category]
        || "Telaryn could not shape this work right now. Nothing was changed.",
    );
  }, []);

  useEffect(() => {
    if (!onRecover) return undefined;
    let active = true;
    onRecover()
      .then((currentAttempt) => {
        if (!active || !currentAttempt) return;
        setExpanded(true);
        updateFromAttempt(currentAttempt);
      })
      .catch(() => {
        // Recovery is best-effort; the user can still begin a new intake.
      });
    return () => {
      active = false;
    };
  }, [onRecover, updateFromAttempt]);

  const attemptIsActive = (
    attempt?.status === "pending" || attempt?.status === "running"
  );
  useEffect(() => {
    if (!attemptIsActive || !onGet) return undefined;
    let active = true;
    const refresh = async () => {
      try {
        const refreshed = await onGet(attempt.id);
        if (active) updateFromAttempt(refreshed);
      } catch {
        // Preserve the visible operation and try again on the next poll.
      }
    };
    const interval = window.setInterval(refresh, 2000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [attempt?.id, attemptIsActive, onGet, updateFromAttempt]);

  function submit(event) {
    event.preventDefault();
    if (!sourceText.trim() || submitting) return;
    if (hasRecentAITransmissionAcknowledgment()) {
      void runIntake();
      return;
    }
    setDisclosureOpen(true);
  }

  function continueWithAI() {
    recordAITransmissionAcknowledgment();
    setDisclosureOpen(false);
    void runIntake();
  }

  async function runIntake() {
    const value = sourceText.trim();
    const controller = new AbortController();
    intakeAbortController.current = controller;
    setSubmitting(true);
    setError(null);
    setProposal(null);
    try {
      const queuedAttempt = await onStart(value, { signal: controller.signal });
      updateFromAttempt(queuedAttempt);
    } catch (err) {
      if (intakeAbortController.current === controller) {
        setSubmitting(false);
        setError(
          err.name === "AbortError"
            ? "Work Intake was cancelled. Nothing was changed."
            : err.message,
        );
      }
    } finally {
      if (intakeAbortController.current === controller) {
        intakeAbortController.current = null;
      }
    }
  }

  async function cancelIntake() {
    intakeAbortController.current?.abort();
    if (!attempt || !onCancel) {
      setSubmitting(false);
      return;
    }
    try {
      updateFromAttempt(await onCancel(attempt.id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function dismissAttempt() {
    if (attempt && onDismiss) await onDismiss(attempt.id);
    setAttempt(null);
  }

  async function editRequest() {
    try {
      await dismissAttempt();
      setProposal(null);
      setSubmitting(false);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }

  function changeClarificationAnswer(index, value) {
    setClarificationAnswers((current) => {
      const next = [...current];
      next[index] = value;
      return next;
    });
  }

  async function refineProposal() {
    if (!attempt || !onRefine) return;
    setSubmitting(true);
    setError(null);
    try {
      updateFromAttempt(await onRefine(attempt.id, clarificationAnswers));
    } catch (err) {
      setSubmitting(false);
      setError(err.message);
    }
  }

  async function discard() {
    try {
      await dismissAttempt();
      setProposal(null);
      setSourceText("");
      setSubmitting(false);
      setError(null);
      setExpanded(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function continueWithProposal(nextSourceText, nextProposal, ticketIndex) {
    try {
      await dismissAttempt();
      onContinue(nextSourceText, nextProposal, ticketIndex);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!expanded) {
    const proposalNeedsInput = proposal?.action === "needs_clarification";
    const hasPendingProposal = Boolean(proposal);
    return (
      <section
        {...sectionProps}
        className={`my-work-guided-intake is-collapsed${prominent ? " is-prominent" : ""}${hasPendingProposal ? " has-proposal" : ""}`}
      >
        <div>
          <div className="work-intake-collapsed-heading">
            <p className="eyebrow">CAPTURE WORK</p>
            {hasPendingProposal && (
              <span className="work-intake-pending-status" role="status">
                {proposalNeedsInput ? "Needs your input" : "Proposal ready"}
              </span>
            )}
          </div>
          <h2>{hasPendingProposal ? proposal.summary : "Something new landed?"}</h2>
          <p>
            {hasPendingProposal
              ? "Nothing has been created yet. Review, refine, continue, or discard this proposal."
              : "Let Telaryn shape how it fits your existing work."}
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={() => setExpanded(true)}>
          {hasPendingProposal
            ? proposalNeedsInput ? "Answer Questions" : "Review Proposal"
            : "Capture New Work"}
        </button>
      </section>
    );
  }

  return (
    <section {...sectionProps} className={`my-work-guided-intake is-expanded${prominent ? " is-prominent" : ""}`}>
      <div className="my-work-guided-intake-heading">
        <div>
          <p className="eyebrow">CAPTURE WORK</p>
          <h2>Something new landed?</h2>
          <p>
            Let Telaryn shape how it fits your existing work by comparing eligible Projects and Tickets before proposing what to do.
          </p>
        </div>
        <button type="button" className="text-button" onClick={() => setExpanded(false)}>
          Collapse
        </button>
      </div>
      {proposal ? (
        <>
          <WorkIntakeProposal
            proposal={proposal}
            sourceText={sourceText.trim()}
            answers={clarificationAnswers}
            refinementCount={attempt?.refinement_count || 0}
            refining={submitting}
            onAnswerChange={changeClarificationAnswer}
            onRefine={refineProposal}
            onCancelRefinement={cancelIntake}
            onEditRequest={editRequest}
            onDiscard={discard}
            onContinue={continueWithProposal}
          />
          {error && <p className="my-work-guided-intake-error" role="alert">{error}</p>}
        </>
      ) : (
        <form onSubmit={submit}>
          <label htmlFor="guided-work-source">What needs to get done?</label>
          <textarea
            id="guided-work-source"
            rows="3"
            value={sourceText}
            onChange={(event) => setSourceText(event.target.value)}
            placeholder="Paste a request, note, or rough idea…"
            disabled={submitting}
          />
          {!sourceText && !submitting && (
            <div className="work-intake-example">
              <div>
                <span>NEED A STARTING POINT?</span>
                <p>Begin with a real outcome, even if the details are still rough.</p>
              </div>
              <button type="button" onClick={() => setSourceText(GUIDED_WORK_EXAMPLE)}>
                Use an example
              </button>
            </div>
          )}
          {error && <p className="my-work-guided-intake-error" role="alert">{error}</p>}
          <div className="my-work-guided-intake-actions">
            <span>Nothing is created until you approve a proposal.</span>
            {submitting ? (
              <AtlasReviewProgress
                onCancel={cancelIntake}
                label={
                  attempt?.status === "pending"
                    ? "Telaryn is preparing to compare this with your work"
                    : "Telaryn is comparing this with your work"
                }
                cancelLabel="Cancel Work Intake"
                compact
              />
            ) : (
              <button type="submit" className="ai-button" disabled={!sourceText.trim()}>
                {error ? "Retry" : "Shape with Telaryn"}
              </button>
            )}
          </div>
        </form>
      )}
      <AITransmissionDisclosure
        open={disclosureOpen}
        onCancel={() => setDisclosureOpen(false)}
        onContinue={continueWithAI}
      />
    </section>
  );
}

function CurrentFocus({
  item,
  canUndoFocus,
  onUndoFocus,
  onOpenTicket,
  onCompleteNextAction,
  onSetAvailability,
  sectionProps = {},
  onFindFocus,
}) {
  const [editingAvailability, setEditingAvailability] = useState(false);
  if (!item) {
    return (
      <section {...sectionProps} className="my-work-current-focus empty">
        <p className="eyebrow">CURRENT FOCUS</p>
        <h2>Choose what gets your attention.</h2>
        <p>Select one of the recommendations below. Telaryn will keep it here without changing its ticket status.</p>
        <button type="button" className="secondary-button" onClick={onFindFocus}>Review suggested work</button>
      </section>
    );
  }

  return (
    <section {...sectionProps} className="my-work-current-focus">
      <header>
        <div>
          <p className="eyebrow">CURRENT FOCUS</p>
          <h2>{item.title}</h2>
          <div className="my-work-item-topline">
            <span>{localTicketReference(item)}</span>
            <span>{item.project_name || "No project"}</span>
          </div>
        </div>
        <span className={`priority ${item.priority}`}>{item.priority}</span>
      </header>
          {canUndoFocus && (
            <div className="my-work-focus-undo" role="status">
              <span>Current Focus changed.</span>
              <button type="button" className="text-button" onClick={onUndoFocus}>Undo</button>
            </div>
          )}

      <div className="my-work-focus-layout">
        <div className="my-work-focus-rationale">
          <span>Why this ticket now</span>
          <p>
            <BreakableTechnicalText>
              {item.focus_rationale || "This ticket is your selected Current Focus."}
            </BreakableTechnicalText>
          </p>
        </div>

        <div className="my-work-next-action">
          <span>Recommended next action</span>
          {item.next_action ? (
            <>
              <h3><BreakableTechnicalText>{item.next_action.title}</BreakableTechnicalText></h3>
              <p>
                {item.next_action.status === "in_progress"
                  ? "Resume the subtask already underway."
                  : "This is the first available concrete step on the ticket."}
              </p>
            </>
          ) : (
            <>
              <h3>No unfinished subtask is available.</h3>
              <p>Add a subtask to give this ticket a concrete next step.</p>
            </>
          )}
          <div className="my-work-card-actions">
            {item.next_action ? (
              <button type="button" className="ai-button" onClick={() => onCompleteNextAction(item)}>
                Mark Complete
              </button>
            ) : (
              <button type="button" className="ai-button" onClick={() => onOpenTicket(item)}>
                Open Ticket to Add One
              </button>
            )}
            <button type="button" className="secondary-button" onClick={() => setEditingAvailability(true)}>Not Now</button>
            <button type="button" className="text-button" onClick={() => onOpenTicket(item)}>Open</button>
          </div>
        </div>
      </div>

      {editingAvailability && (
        <AvailabilityEditor
          item={item}
          onApply={(ticket, mode, availableOn) => {
            onSetAvailability(ticket, mode, availableOn);
            setEditingAvailability(false);
          }}
          onCancel={() => setEditingAvailability(false)}
        />
      )}
    </section>
  );
}

function CompactSection({
  eyebrow,
  title,
  items,
  onOpenTicket,
  collapsible = false,
  emptyMessage = "Nothing needs your attention here.",
  sectionProps = {},
}) {
  const ticketList = items.length ? (
    <div className="my-work-list compact">
      {items.map((item) => (
        <button key={item.id} className="my-work-item" type="button" onClick={() => onOpenTicket(item)}>
          <TicketContext item={item} />
        </button>
      ))}
    </div>
  ) : (
    <p className="my-work-state">{emptyMessage}</p>
  );

  if (collapsible) {
    return (
      <details {...sectionProps} className="my-work-section my-work-collapsible">
        <summary className="my-work-section-header">
          <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>
          <span className="my-work-count">{items.length}</span>
        </summary>
        {ticketList}
      </details>
    );
  }

  return (
    <section {...sectionProps} className="my-work-section">
      <header className="my-work-section-header">
        <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>
        <span className="my-work-count">{items.length}</span>
      </header>
      {ticketList}
    </section>
  );
}

function UpcomingWork({ items, onMakeAvailable, onOpenTicket }) {
  if (!items.length) return null;
  return (
    <section className="my-work-section my-work-upcoming">
      <header className="my-work-section-header">
        <div>
          <p className="eyebrow">UPCOMING WORK</p>
          <h2>Not actionable yet</h2>
          <p>Important work you intentionally removed from consideration for now.</p>
        </div>
        <span className="my-work-count">{items.length}</span>
      </header>
      <div className="my-work-list compact">
        {items.map((item) => (
          <article key={item.id} className="my-work-item">
            <TicketContext item={item} />
            <p className="my-work-availability">
              {item.availability_mode === "date"
                ? `Available ${formatDate(item.available_on)}`
                : item.availability_mode === "context_change"
                  ? "Returns when the ticket changes"
                  : "Hidden until you restore it"}
            </p>
            <div className="my-work-card-actions">
              <button type="button" className="secondary-button" onClick={() => onMakeAvailable(item)}>Make Available Now</button>
              <button type="button" className="text-button" onClick={() => onOpenTicket(item)}>Open Ticket</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MyWorkView({
  work,
  loading,
  error,
  onOpenTicket,
  onSetFocus,
  onUndoFocus,
  canUndoFocus,
  onSetAvailability,
  onMakeAvailable,
  onCompleteNextAction,
  onStartGuidedIntake,
  onRefineGuidedIntake,
  onRecoverGuidedIntake,
  onGetGuidedIntake,
  onCancelGuidedIntake,
  onDismissGuidedIntake,
  onContinueGuidedIntake,
  guidedIntakeResetVersion,
  activeSectionId = DEFAULT_MY_WORK_SECTION,
  navigationRequest,
  onActiveSectionChange,
  onNavigateSection,
  onboardingPanel,
}) {
  const mainRef = useRef(null);

  function sectionProps(sectionId) {
    return {
      id: `my-work-${sectionId}`,
      "data-my-work-section": sectionId,
      tabIndex: -1,
    };
  }

  useEffect(() => {
    if (!navigationRequest?.version) return;
    const section = mainRef.current?.querySelector(
      `[data-my-work-section="${navigationRequest.sectionId}"]`,
    );
    if (!section) return;
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    section.scrollIntoView?.({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }, [navigationRequest]);

  useEffect(() => {
    const scrollPanel = mainRef.current;
    if (!scrollPanel || !onActiveSectionChange) return undefined;
    let frame = null;

    const updateActiveSection = () => {
      frame = null;
      const availableSections = MY_WORK_SECTIONS
        .map(({ id }) => {
          const node = scrollPanel.querySelector(`[data-my-work-section="${id}"]`);
          return { id, node, rect: node?.getBoundingClientRect() };
        })
        .filter(({ node }) => Boolean(node));
      if (
        !availableSections.length
        || availableSections.every(({ rect }) => !rect?.height)
      ) return;

      if (
        scrollPanel.scrollHeight > scrollPanel.clientHeight
        && scrollPanel.scrollTop + scrollPanel.clientHeight >= scrollPanel.scrollHeight - 4
      ) {
        onActiveSectionChange(availableSections.at(-1).id);
        return;
      }

      const panelTop = scrollPanel.getBoundingClientRect().top;
      const readingLine = panelTop + Math.min(140, scrollPanel.clientHeight * 0.28);
      let nextSection = availableSections[0].id;
      availableSections.forEach(({ id, rect }) => {
        if (rect.top <= readingLine) nextSection = id;
      });
      onActiveSectionChange(nextSection);
    };

    const scheduleUpdate = () => {
      if (frame !== null) return;
      frame = window.requestAnimationFrame(updateActiveSection);
    };

    scrollPanel.addEventListener("scroll", scheduleUpdate, { passive: true });
    window.addEventListener("resize", scheduleUpdate);
    frame = window.requestAnimationFrame(updateActiveSection);
    return () => {
      scrollPanel.removeEventListener("scroll", scheduleUpdate);
      window.removeEventListener("resize", scheduleUpdate);
      if (frame !== null) window.cancelAnimationFrame(frame);
    };
  }, [onActiveSectionChange, work]);

  const hasExistingWork = Boolean(
    work?.current_focus
      || work?.suggestions?.length
      || work?.upcoming?.length
      || work?.ready_later_count
      || work?.needs_attention?.length
      || work?.in_review?.length
      || work?.recently_completed?.length
  );

  return (
    <main ref={mainRef} className="main-content my-work-view">
      <header className="topbar my-work-topbar">
        <div>
          <p className="eyebrow">PERSONAL EXECUTION</p>
          <h1>Your next move, clearly.</h1>
          <p className="my-work-intro">
            One focus across projects, with three meaningful alternatives close at hand.
          </p>
        </div>
      </header>

      <label className="my-work-mobile-section-nav">
        <span>Jump to</span>
        <select
          aria-label="Jump to My Work section"
          value={activeSectionId}
          onChange={(event) => onNavigateSection?.(event.target.value)}
        >
          {MY_WORK_SECTIONS.map((section) => (
            <option key={section.id} value={section.id}>{section.label}</option>
          ))}
        </select>
      </label>

      {onboardingPanel}

      {loading && !work && <div className="my-work-state">Building your focus stack…</div>}
      {error && <div className="my-work-state error">{error}</div>}

      {work && (
        <>
          {!hasExistingWork && (
            <GuidedWorkIntake
              key={`guided-intake-${guidedIntakeResetVersion}`}
              prominent
              sectionProps={sectionProps("capture-work")}
              onStart={onStartGuidedIntake}
              onRefine={onRefineGuidedIntake}
              onRecover={onRecoverGuidedIntake}
              onGet={onGetGuidedIntake}
              onCancel={onCancelGuidedIntake}
              onDismiss={onDismissGuidedIntake}
              onContinue={onContinueGuidedIntake}
            />
          )}

          <CurrentFocus
            item={work.current_focus}
            canUndoFocus={canUndoFocus}
            onUndoFocus={onUndoFocus}
            onOpenTicket={onOpenTicket}
            onCompleteNextAction={onCompleteNextAction}
            onSetAvailability={onSetAvailability}
            onFindFocus={() => onNavigateSection?.("suggested-next")}
            sectionProps={sectionProps("current-focus")}
          />

          <section {...sectionProps("suggested-next")} className="my-work-suggestions">
            <header className="my-work-section-header">
              <div>
                <p className="eyebrow">SUGGESTED NEXT</p>
                <h2>Other meaningful options</h2>
                <p>Choose one only when it deserves your attention more.</p>
              </div>
              <span className="my-work-count">{work.suggestions.length}</span>
            </header>
            {work.suggestions.length ? (
              <div className="my-work-suggestion-grid">
                {work.suggestions.map((item) => (
                  <SuggestionCard
                    key={item.id}
                    item={item}
                    onFocus={onSetFocus}
                    onOpenTicket={onOpenTicket}
                    onSetAvailability={onSetAvailability}
                  />
                ))}
              </div>
            ) : (
              <p className="my-work-state">No additional work is currently available for focus.</p>
            )}
            {work.ready_later_count > 0 && (
              <p className="my-work-overflow-note">
                {work.ready_later_count} additional eligible {work.ready_later_count === 1 ? "ticket remains" : "tickets remain"} in Projects.
              </p>
            )}
          </section>

          {hasExistingWork && (
            <GuidedWorkIntake
              key={`guided-intake-${guidedIntakeResetVersion}`}
              sectionProps={sectionProps("capture-work")}
              onStart={onStartGuidedIntake}
              onRefine={onRefineGuidedIntake}
              onRecover={onRecoverGuidedIntake}
              onGet={onGetGuidedIntake}
              onCancel={onCancelGuidedIntake}
              onDismiss={onDismissGuidedIntake}
              onContinue={onContinueGuidedIntake}
            />
          )}

          <UpcomingWork
            items={work.upcoming}
            onMakeAvailable={onMakeAvailable}
            onOpenTicket={onOpenTicket}
          />
          <div className="my-work-supporting-grid">
            <CompactSection
              eyebrow="NEEDS ATTENTION"
              title="Clear the friction"
              items={work.needs_attention}
              onOpenTicket={onOpenTicket}
              emptyMessage="Nothing currently needs intervention."
              sectionProps={sectionProps("needs-attention")}
            />
            <CompactSection eyebrow="IN REVIEW" title="Close the loop" items={work.in_review} onOpenTicket={onOpenTicket} />
          </div>
          <CompactSection
            eyebrow="RECENT PROGRESS"
            title="What you moved forward"
            items={work.recently_completed}
            onOpenTicket={onOpenTicket}
            collapsible
            emptyMessage="Completed work will appear here."
            sectionProps={sectionProps("recent-progress")}
          />
        </>
      )}
    </main>
  );
}

export default MyWorkView;
