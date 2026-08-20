import { EmptySection } from "./KnowledgeCard";

// MWO-LTSA-032A -- KnowledgeSeal: Mechanical Seal body (KnowledgeCard
// variant="kv"). Repository Archaeology (via EngineeringContextEngine's
// own disclosed gap) confirmed no backend data source distinguishes "the
// seal currently installed on this pump" from "seals compatible with this
// pump type" -- so `seal` here is always undefined against real data, and
// this section always renders its empty state. Compatible Seals (a
// different section, real data) is rendered separately, not from here.
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
      <Row label="Type" value={seal.type} />
      <Row label="API Plan" value={seal.apiPlan} />
      <Row label="Installed" value={seal.installedDate} />
      <Row label="Hours" value={seal.hours} />
      <Row label="MTBF" value={seal.mtbf} />
    </div>
  );
}
