import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeSummary: Equipment Summary body (KnowledgeCard
// variant="grid"). Every field that isn't available from the real
// Knowledge API (location, healthScore, criticality, confidence) renders
// "Unavailable" rather than a fabricated value -- disclosed in the
// deliverable report's Reuse/Architecture Impact sections.
function Field({ label, value }) {
  return (
    <div className="eng-summary-field">
      <span className="eng-kicker">{label}</span>
      <span className="v">{value ?? "Unavailable"}</span>
    </div>
  );
}

export default function KnowledgeSummary({ equipment }) {
  if (!equipment) {
    return <EmptySection title="Belum ada data peralatan" />;
  }

  return (
    <div className="eng-summary-grid" data-testid="knowledge-summary">
      <Field label="Tag" value={equipment.tag} />
      <Field label="Name" value={equipment.name} />
      <Field label="Location" value={equipment.location} />
      <Field label="Status" value={equipment.status} />
      <Field label="Last Updated" value={equipment.lastUpdated} />
      {equipment.aiSummary ? <p className="eng-summary-ai">{equipment.aiSummary}</p> : null}
    </div>
  );
}
