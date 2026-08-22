// MWO-LTSA-032A -- KnowledgeSeal: Mechanical Seal body (KnowledgeCard
// variant="kv"). Compatible Seals (a different section) is rendered
// separately, not from here.
//
// MWO-LTSA-ASSET360-SEAL-SEMANTICS-001 -- two deliberately distinct
// concepts, never merged: CONFIGURED/DESIGN DATA (ltsa_pumps.seal_type /
// ltsa_pumps.api_plan -- master data describing what the pump is designed
// for, always shown when known) and CURRENT INSTALLATION (current_seal --
// authoritative evidence of what is actually installed today, from
// EquipmentTimelineService.build_current_seal(), MWO-LTSA-ASSET360-
// MECHANICAL-SEAL-WIRING-001). seal_type is broad/non-unique (production
// evidence: 16 different seal_registry T48MP variants exist with
// different shaft_size values) and installation_report currently has zero
// production rows, so seal_type must NEVER be treated as proof of, or
// mapped onto, a specific current installation -- that would fabricate an
// identity the data does not support. When current_seal is null, every
// current-installation row still renders, falling back to "Not recorded"
// (fallback prop below), never inferred from configuredSeal.
function Row({ label, value, fallback = "Unavailable" }) {
  return (
    <div className="info-row">
      <span className="k">{label}</span>
      <span className="v">{value ?? fallback}</span>
    </div>
  );
}

export default function KnowledgeSeal({ configuredSeal, currentSeal }) {
  return (
    <div data-testid="knowledge-seal">
      <div className="knowledge-seal-group" data-testid="knowledge-seal-configured">
        <h4 className="knowledge-seal-subhead">Configured / Design Data</h4>
        <Row label="Configured Seal Type" value={configuredSeal?.sealType} />
        <Row label="API Plan" value={configuredSeal?.apiPlan} />
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-current">
        <h4 className="knowledge-seal-subhead">Current Installation</h4>
        <span className={`status-signal ${currentSeal?.status ?? ""}`}>
          <span className="dot-lg" />
          {currentSeal?.status ?? "Unknown"}
        </span>
        <Row label="Current Installed Seal" value={currentSeal?.code} fallback="Not recorded" />
        <Row label="Name" value={currentSeal?.name} fallback="Not recorded" />
        <Row label="Manufacturer" value={currentSeal?.manufacturer} fallback="Not recorded" />
        <Row label="Model" value={currentSeal?.model} fallback="Not recorded" />
        <Row label="Material" value={currentSeal?.material} fallback="Not recorded" />
        <Row label="Installed Date" value={currentSeal?.installedDate} fallback="Not recorded" />
      </div>
    </div>
  );
}
