// Presents rich project context without allowing long narrative fields to dominate the page.
import { useLayoutEffect, useRef, useState } from "react";
import { projectLifeContextLabel } from "../../projectLifeContexts";

function ExpandableProjectContext({ projectId, label, text, emptyText }) {
  const [expandedProjectId, setExpandedProjectId] = useState(null);
  const [overflowing, setOverflowing] = useState(false);
  const textRef = useRef(null);
  const expanded = expandedProjectId === projectId;
  const hasText = Boolean(text?.trim());

  useLayoutEffect(() => {
    if (!hasText || !textRef.current) {
      setOverflowing(false);
      return undefined;
    }

    const element = textRef.current;
    const measure = () => {
      setOverflowing(element.scrollHeight > element.clientHeight + 1);
    };
    measure();
    window.addEventListener("resize", measure);
    const observer =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    observer?.observe(element);

    return () => {
      window.removeEventListener("resize", measure);
      observer?.disconnect();
    };
  }, [hasText, projectId, text]);

  return (
    <div className={`project-context-item ${hasText ? "" : "empty"}`}>
      <span>{label}</span>
      <p
        id={`project-${projectId}-${label.toLowerCase().replaceAll(" ", "-")}`}
        ref={textRef}
        className={`preserve-line-breaks ${expanded ? "expanded" : "collapsed"}`}
      >
        {text || emptyText}
      </p>
      {hasText && (overflowing || expanded) && (
        <button
          type="button"
          className="project-context-toggle"
          aria-expanded={expanded}
          aria-controls={`project-${projectId}-${label
            .toLowerCase()
            .replaceAll(" ", "-")}`}
          onClick={() => setExpandedProjectId(expanded ? null : projectId)}
        >
          {expanded ? "Show Less" : "Show More"}
        </button>
      )}
    </div>
  );
}

function ProjectContextPanel({ project }) {
  return (
    <>
      {project.ai_context_enabled === false && (
        <aside className="project-private-notice">
          <strong>Private project</strong>
          <span>
            Telaryn will not send this project’s content to an AI provider.
            Workspace access is unchanged.
          </span>
        </aside>
      )}
      <section className="project-intent">
        <p className="eyebrow">PROJECT INTENT</p>
        <p className="project-life-context">
          Activity Report context: <strong>{projectLifeContextLabel(project.life_context)}</strong>
        </p>
        <div className="project-intent-content">
          <ExpandableProjectContext
            projectId={project.id}
            label="Purpose"
            text={project.purpose}
            emptyText="Add the outcome this project is working toward."
          />
          <ExpandableProjectContext
            projectId={project.id}
            label="Why it matters now"
            text={project.why_it_matters}
            emptyText="Add the need, commitment, or personal value behind this work."
          />
        </div>
      </section>

      <details key={project.id} className="project-about">
        <summary>
          <span>
            <small>ABOUT THIS PROJECT</small>
            <strong>Description and supporting context</strong>
          </span>
          <span className="project-about-action">Show</span>
        </summary>
        <p className="preserve-line-breaks">
          {project.description
            || "Add a description to explain this project’s scope and background."}
        </p>
      </details>
    </>
  );
}

export function ProjectPublicReference({ project }) {
  const [copied, setCopied] = useState(false);

  async function copyReference() {
    if (!project.public_id) return;
    try {
      if (window.navigator.clipboard?.writeText) {
        await window.navigator.clipboard.writeText(project.public_id);
      } else {
        const input = document.createElement("textarea");
        input.value = project.public_id;
        input.setAttribute("readonly", "");
        input.style.position = "fixed";
        input.style.opacity = "0";
        document.body.appendChild(input);
        input.select();
        const copiedReference = document.execCommand("copy");
        input.remove();
        if (!copiedReference) throw new Error("Copy unavailable");
      }
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  if (!project.public_id) return null;

  return (
    <p className="project-public-reference">
      <code title={project.public_id}>{project.public_id}</code>
      <button type="button" className="text-button" onClick={copyReference}>
        {copied ? "Copied" : "Copy reference"}
      </button>
    </p>
  );
}

export default ProjectContextPanel;

