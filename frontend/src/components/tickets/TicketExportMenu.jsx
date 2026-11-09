// Owns authorized Ticket file retrieval and the browser download interaction.
import { useRef, useState } from "react";

import { downloadTicketExport } from "../../api";

function saveDownload({ blob, filename }) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function TicketExportMenu({ ticketId }) {
  const detailsRef = useRef(null);
  const [exporting, setExporting] = useState(null);
  const [error, setError] = useState("");

  async function exportTicket(format) {
    setExporting(format);
    setError("");
    try {
      saveDownload(await downloadTicketExport(ticketId, format));
      detailsRef.current?.removeAttribute("open");
    } catch (exportError) {
      setError(exportError.message || "Telaryn could not export this Ticket.");
    } finally {
      setExporting(null);
    }
  }

  return (
    <div className="ticket-export-control">
      <details ref={detailsRef} className="ticket-export-menu">
        <summary>Export</summary>
        <div role="menu" aria-label="Export Ticket">
          <button type="button" role="menuitem" disabled={Boolean(exporting)} onClick={() => exportTicket("json")}>
            <strong>{exporting === "json" ? "Preparing JSON…" : "Machine-readable JSON"}</strong>
            <span>Structured, versioned Ticket data</span>
          </button>
          <button type="button" role="menuitem" disabled={Boolean(exporting)} onClick={() => exportTicket("pdf")}>
            <strong>{exporting === "pdf" ? "Preparing PDF…" : "Human-readable PDF"}</strong>
            <span>Formatted for reading, printing, or sharing</span>
          </button>
        </div>
      </details>
      {error && <p className="ticket-export-error" role="alert">{error}</p>}
    </div>
  );
}

