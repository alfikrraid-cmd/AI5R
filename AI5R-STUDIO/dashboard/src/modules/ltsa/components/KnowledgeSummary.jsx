import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeSummary: Equipment Summary body (KnowledgeCard
// variant="grid"). Every field that isn't available from the real
// Knowledge API (healthScore, criticality, confidence) renders
// "Unavailable" rather than a fabricated value -- disclosed in the
// deliverable report's Reuse/Architecture Impact sections.
//
// MWO-LTSA-ASSET360-UI-PRODUCTION-HARDENING-001 -- Area/Location are two
// distinct, both-honest fields (production evidence: 212-P-7B has
// area="Reaktor" but location=null) -- neither is hidden in favor of the
// other, and Location is never fabricated from Area. Asset Status
// (ltsa_pumps.status master-data column, e.g. "UNKNOWN") and Condition
// (a derived health/risk assessment from condition-monitoring evidence,
// e.g. "normal") are likewise two distinct fields, never collapsed into
// one ambiguous "Status" -- see useKnowledgeWorkspace.js's mapEquipment
// for the full provenance rationale. "Generated At" (not "Last Updated")
// is deliberately honest about what the timestamp actually measures: the
// moment this Knowledge aggregate was computed, not when the pump's own
// master data last changed.
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
      <Field label="Area" value={equipment.area} />
      <Field label="Location" value={equipment.location} />
      <Field label="Pump Type" value={equipment.pumpType} />
      <Field label="Asset Status" value={equipment.assetStatus} />
      <Field label="Condition" value={equipment.condition} />
      <Field label="Generated At" value={equipment.lastUpdated} />
      {equipment.aiSummary ? <p className="eng-summary-ai">{equipment.aiSummary}</p> : null}
    </div>
  );
}
