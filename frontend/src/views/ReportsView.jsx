// Presents report configuration while the server owns authorization and evidence selection.
import { useEffect, useState } from "react";
import { projectArchiveReasonLabel } from "../projectArchiveReasons";
import { projectLifeContextLabel } from "../projectLifeContexts";
import "./ReportsView.css";

const SCOPE_OPTIONS = ["work", "volunteer", "personal", "all"];

function dateInputValue(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultReportDateRange(period, through = new Date()) {
  const start = new Date(through);
  if (period === "weekly") start.setDate(start.getDate() - 6);
  if (period === "monthly") start.setDate(1);
  if (period === "quarterly") {
    start.setMonth(Math.floor(start.getMonth() / 3) * 3, 1);
  }
  if (period === "annual") {
    start.setDate(start.getDate() + 1);
    start.setFullYear(start.getFullYear() - 1);
  }
  return { start: dateInputValue(start), end: dateInputValue(through) };
}

export default function ReportsView({ loadProjects, onGenerate, onRequestAITransmission }) {
  const [projects, setProjects] = useState([]);
  const [scope, setScope] = useState("work");
  const [period, setPeriod] = useState("weekly");
  const [dateRange, setDateRange] = useState(() => defaultReportDateRange("weekly"));
  const [outputFormat, setOutputFormat] = useState("narrative");
  const [styleExample, setStyleExample] = useState("");
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  useEffect(() => {
    loadProjects()
      .then((loadedProjects) => {
        setProjects(loadedProjects);
        setSelectedIds(new Set(loadedProjects.filter((project) =>
          project.included_by_default && project.life_context === "work"
        ).map((project) => project.id)));
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoadingProjects(false));
  }, [loadProjects]);

  function selectScope(nextScope) {
    setScope(nextScope);
    setSelectedIds(new Set(projects.filter((project) =>
      project.included_by_default
      && (nextScope === "all" || project.life_context === nextScope)
    ).map((project) => project.id)));
  }

  function toggleProject(projectId) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  }

  function selectPeriod(nextPeriod) {
    setPeriod(nextPeriod);
    setDateRange(defaultReportDateRange(nextPeriod));
  }

  async function performGenerate() {
    setGenerating(true);
    setError(null);
    try {
      setReport(await onGenerate({
        period,
        output_format: outputFormat,
        scope,
        project_ids: [...selectedIds],
        style_example: styleExample.trim() || null,
        period_start: dateRange.start,
        period_end: dateRange.end,
      }));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setGenerating(false);
    }
  }

  function generate(event) {
    event.preventDefault();
    onRequestAITransmission(performGenerate);
  }

  return (
    <main className="main-content reports-page">
      <header className="reports-hero">
        <p className="eyebrow">ACTIVITY REPORTS</p>
        <h1>Turn progress into a useful story.</h1>
        <p>Choose the audience, time period, evidence, and format. Telaryn summarizes only the work you approve.</p>
      </header>

      <div className="reports-layout">
        <form className="report-config" onSubmit={generate}>
          <section className="report-config-section report-settings-section">
            <header><p className="eyebrow">REPORT SETTINGS</p><h2>Shape the report</h2></header>
            <div className="report-field-grid">
              <label><span>Life context</span><select value={scope} onChange={(event) => selectScope(event.target.value)}>
                {SCOPE_OPTIONS.map((value) => <option key={value} value={value}>{value === "all" ? "All contexts" : projectLifeContextLabel(value)}</option>)}
              </select></label>
              <label><span>Period preset</span><select value={period} onChange={(event) => selectPeriod(event.target.value)}>
                <option value="weekly">Weekly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="annual">Past 12 Months</option>
              </select></label>
              <label><span>Format</span><select value={outputFormat} onChange={(event) => setOutputFormat(event.target.value)}>
                <option value="narrative">Narrative paragraphs</option><option value="action_result_impact">Action – Result – Impact</option>
              </select></label>
            </div>

            <div className="report-date-grid">
              <label><span>From</span><input type="date" value={dateRange.start} max={dateRange.end} onChange={(event) => setDateRange((current) => ({ ...current, start: event.target.value }))} /></label>
              <label><span>Through</span><input type="date" value={dateRange.end} min={dateRange.start} onChange={(event) => setDateRange((current) => ({ ...current, end: event.target.value }))} /></label>
            </div>
          </section>

          <section className="report-config-section report-evidence-section">
            <header><p className="eyebrow">EVIDENCE</p><h2>Choose the work</h2></header>
            <div className="report-project-field">
              <span>Projects to include</span>
              <small>Active Projects are eligible. Completed archives may be included by default; other archived classifications remain excluded unless you deliberately select them.</small>
              <details className="report-project-picker">
                <summary>
                  <span>{selectedIds.size === 1 ? "1 Project selected" : `${selectedIds.size} Projects selected`}</span>
                  <strong>Choose</strong>
                </summary>
                <div role="group" aria-label="Projects to include">
                  {loadingProjects ? <p>Loading eligible Projects…</p> : projects.map((project) => (
                    <label key={project.id} className={project.life_context !== scope && scope !== "all" ? "outside-scope" : ""}>
                      <input type="checkbox" checked={selectedIds.has(project.id)} onChange={() => toggleProject(project.id)} />
                      <span><strong>{project.name}</strong><small>{projectLifeContextLabel(project.life_context)}{project.archived ? ` · Archived: ${projectArchiveReasonLabel(project.archive_reason)}` : ""}</small></span>
                    </label>
                  ))}
                </div>
              </details>
            </div>
          </section>

          <details className="report-style-example report-config-section">
            <summary><span><small className="eyebrow">OPTIONAL GUIDANCE</small><b>Style example</b></span><strong>{styleExample ? "Added" : "Add"}</strong></summary>
            <div>
              <small>Use this to guide tone and structure. Telaryn treats it as style—not evidence.</small>
              <textarea aria-label="Style example" rows="5" maxLength="4000" value={styleExample} onChange={(event) => setStyleExample(event.target.value)} placeholder="Paste a short example of how you want the report to sound…" />
            </div>
          </details>

          <aside className="report-ai-note"><strong>Before Telaryn generates</strong><span>Your selected Project and Ticket activity will be sent to the configured AI provider. Projects and Tickets marked Private—and their related activity—are excluded before anything is submitted. Do not include sensitive information or PII in the style example.</span></aside>
          {error && <p className="ai-review-error" role="alert">{error}</p>}
          <button className="ai-button" disabled={generating || selectedIds.size === 0}>{generating ? "Telaryn is shaping your report…" : "Generate Activity Report"}</button>
        </form>

        <section className="report-preview" aria-live="polite">
          <p className="eyebrow">REPORT PREVIEW</p>
          {report ? <><h2>{report.title}</h2><p className="muted">{report.period_start} through {report.period_end}</p><div className="report-items">{report.items.map((item, index) => <p key={`${index}-${item.slice(0, 20)}`}>{item}</p>)}</div></> : <><h2>Your report will appear here.</h2><p>Select the evidence Telaryn should use, then review the generated result before sharing it.</p></>}
        </section>
      </div>
    </main>
  );
}
