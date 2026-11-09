// Download the complete authorized Project snapshot as versioned JSON.
import { useState } from "react";

import { downloadProjectExport } from "../../api";

export default function ProjectExportButton({ projectId }) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  async function exportProject() {
    setExporting(true);
    setError("");
    try {
      const { blob, filename } = await downloadProjectExport(projectId);
      const url = URL.createObjectURL(blob);
      try {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
      } finally {
        URL.revokeObjectURL(url);
      }
    } catch (cause) {
      setError(cause.message || "Telaryn could not export this Project.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="project-export-control">
      <button
        type="button"
        className="secondary-button"
        aria-label="Export Project JSON"
        title="Download Project metadata, all Tickets (including Private Tickets), and their histories"
        disabled={exporting}
        onClick={exportProject}
      >
        {exporting ? "Preparing JSON…" : "Export Project JSON"}
      </button>
      {error && <p className="project-export-error" role="alert">{error}</p>}
    </div>
  );
}
