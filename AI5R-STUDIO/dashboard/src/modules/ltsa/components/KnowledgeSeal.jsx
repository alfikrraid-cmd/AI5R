import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeSeal: Mechanical Seal body (KnowledgeCard
// variant="kv"). Compatible Seals (a different section) is rendered
// separately, not from here.
//
// MWO-LTSA-ASSET360-MECHANICAL-SEAL-WIRING-001 -- `seal` is now populated
// from the Knowledge API's `current_seal` (see useKnowledgeWorkspace.js's
// mapMechanicalSeal) when the pump has an authoritative current
// installation; still undefined (empty state below) when it does not --
// never fabricated either way. `type`/`apiPlan`/`hours`/`mtbf` remain
// unset regardless (no authoritative source anywhere in the backend
// derivation), rendered honestly as "Unavailable" by Row below.
function Row({ label, value }) {
  return (
    <div className="info-row">
      <span className="k">{label}</span>
      <span className="v">{value ?? "Unavailable"}</span>
    </div>
  );
}

export default function KnowledgeSeal({ seal }) {
  if (!seal) {
    return (
      <EmptySection
        title="Belum ada seal terpasang"
        description="Data seal terpasang belum tersedia dari sistem."
      />
    );
  }

  return (
    <div data-testid="knowledge-seal">
      <span className={`status-signal ${seal.status ?? ""}`}>
        <span className="dot-lg" />
        {seal.status ?? "Unknown"}
      </span>
      <Row label="Code" value={seal.code} />
      <Row label="Name" value={seal.name} />
      <Row label="Manufacturer" value={seal.manufacturer} />
      <Row label="Model" value={seal.model} />
      <Row label="Material" value={seal.material} />
      <Row label="Type" value={seal.type} />
      <Row label="API Plan" value={seal.apiPlan} />
      <Row label="Installed" value={seal.installedDate} />
      <Row label="Hours" value={seal.hours} />
      <Row label="MTBF" value={seal.mtbf} />
    </div>
  );
}
