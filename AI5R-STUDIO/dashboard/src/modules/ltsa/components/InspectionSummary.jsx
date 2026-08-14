export default function InspectionSummary({ summary }) {
  return (
    <div className="inspection-summary" aria-label="Inspection summary">
      <div>
        <strong>{summary.total} inspections</strong>
        <span>Total history</span>
      </div>
      <div>
        <strong>{summary.findings} findings</strong>
        <span>Recorded findings</span>
      </div>
      <div>
        <strong>{summary.latestDate || "—"}</strong>
        <span>Latest inspection</span>
      </div>
    </div>
  );
}
