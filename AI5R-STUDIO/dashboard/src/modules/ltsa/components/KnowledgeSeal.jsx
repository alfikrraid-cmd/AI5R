import KnowledgeCompatibleSeals from "./KnowledgeCompatibleSeals";
import { EmptySection } from "./KnowledgeCard";
import { mapCurrentInstallation } from "../utils/currentInstallationMapping";

// MWO-LTSA-032A -- KnowledgeSeal: Asset 360's Mechanical Seal body.
//
// LTSA_ASSET360_CURRENT_INSTALLATION_AND_SERVICE_AGE_R1 -- the per-asset
// Mechanical Seal destination (main column), consolidating what the
// inspector rail used to repeat. Four concepts stay strictly separate:
//   - Configured / Design: ltsa_pumps.seal_type / api_plan (master data)
//   - Current Installation: installation evidence only (backend
//     current_installation contract) -- never filled from the configured
//     seal, compatibility, or the seal_registry catalog status
//   - Time Since Installation: CALENDAR time since that installation,
//     never operating/running hours (Actual Operating Hours stays N/A
//     until a runtime/hour-meter source exists)
//   - Compatible Seals: what COULD be fitted, never what IS fitted
// Absent evidence renders "Not Recorded"; absent numbers render "N/A".

const NOT_RECORDED = "Not Recorded";
const NOT_AVAILABLE = "N/A";

function Row({ label, value, fallback = NOT_RECORDED, testId }) {
  return (
    <div className="info-row" data-testid={testId}>
      <span className="k">{label}</span>
      <span className="v">{value ?? fallback}</span>
    </div>
  );
}

function formatCount(value, unit) {
  return value === undefined ? undefined : `${value.toLocaleString("en-US")} ${unit}`;
}

function CurrentInstallationRows({ installation }) {
  return (
    <>
      <span className={`status-signal ${installation.status.toLowerCase()}`} data-testid="installation-status">
        <span className="dot-lg" />
        {installation.statusLabel}
      </span>
      <Row label="Installation Status" value={installation.statusLabel} />
      <Row label="Installed Seal Type" value={installation.installedSealType} />
      <Row label="Installed Seal Unit" value={installation.installedSealUnit} />
      <Row label="Position" value={installation.position} />
      <Row label="Installation Date" value={installation.installationDate} />
      {installation.removedAt ? <Row label="Removed" value={installation.removedAt} /> : null}
      <Row label="Source" value={installation.sourceDocument ?? installation.sourceInstallationCode} />
    </>
  );
}

function TimeSinceInstallation({ installation }) {
  return (
    <>
      <Row
        label="Days Since Installation"
        value={formatCount(installation.daysSinceInstallation, "days")}
        fallback={NOT_AVAILABLE}
        testId="time-since-days"
      />
      <Row
        label="Hours Since Installation"
        value={formatCount(installation.hoursSinceInstallation, "hours")}
        fallback={NOT_AVAILABLE}
        testId="time-since-hours"
      />
      <Row label="Basis" value={installation.timeBasisLabel} testId="time-since-basis" />
      <Row label="Precision" value={installation.timePrecisionLabel} fallback={NOT_AVAILABLE} testId="time-since-precision" />
    </>
  );
}

function InstallationHistory({ events }) {
  if (!events.length) {
    return <EmptySection title="No installation history recorded" />;
  }
  return events.map((event) => (
    <div className="part-item" key={event.code} data-testid={`installation-history-${event.code}`}>
      <div className="part-row">
        <span className="part-name">{event.date ?? NOT_RECORDED}</span>
        <span>{event.code}</span>
      </div>
      <div className="part-meta">
        Installed Seal Type: {event.sealType ?? NOT_RECORDED} · Position: {event.position ?? NOT_RECORDED}
      </div>
      <div className="part-meta">Source: {event.sourceDocument ?? NOT_RECORDED}</div>
    </div>
  ));
}

export default function KnowledgeSeal({
  configuredSeal,
  currentInstallation,
  currentInstallations = [],
  installationHistory = [],
  compatibleSeals = [],
}) {
  const primary = currentInstallation ?? mapCurrentInstallation(null);
  // One block per evidenced position (DE/NDE/pump-level); a single
  // NOT_RECORDED block when there is no installation evidence at all.
  const installations = currentInstallations.length ? currentInstallations : [primary];
  const multiple = installations.length > 1;

  return (
    <div data-testid="knowledge-seal">
      <div className="knowledge-seal-group" data-testid="knowledge-seal-configured">
        <h4 className="knowledge-seal-subhead">Configured / Design</h4>
        <Row label="Configured Seal" value={configuredSeal?.sealType} />
        <Row label="API Plan" value={configuredSeal?.apiPlan} />
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-current">
        <h4 className="knowledge-seal-subhead">Current Installation</h4>
        {installations.map((installation, index) => (
          <div key={installation.sourceInstallationCode ?? index} data-testid="current-installation-entry">
            {multiple ? <h5 className="knowledge-seal-subhead">Position {installation.position ?? NOT_RECORDED}</h5> : null}
            <CurrentInstallationRows installation={installation} />
          </div>
        ))}
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-time">
        <h4 className="knowledge-seal-subhead">Time Since Installation</h4>
        {installations.map((installation, index) => (
          <div key={installation.sourceInstallationCode ?? index}>
            {multiple ? <h5 className="knowledge-seal-subhead">Position {installation.position ?? NOT_RECORDED}</h5> : null}
            <TimeSinceInstallation installation={installation} />
          </div>
        ))}
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-operating-hours">
        <h4 className="knowledge-seal-subhead">Actual Operating Hours</h4>
        <Row label="Actual Operating Hours" value={formatCount(primary.actualOperatingHours, "hours")} fallback={NOT_AVAILABLE} />
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-compatible">
        <h4 className="knowledge-seal-subhead">Compatible Seals</h4>
        <KnowledgeCompatibleSeals items={compatibleSeals} emptyTitle="Belum ada seal kompatibel" />
      </div>

      <div className="knowledge-seal-group" data-testid="knowledge-seal-history">
        <h4 className="knowledge-seal-subhead">Lifecycle / Installation History</h4>
        <InstallationHistory events={installationHistory} />
      </div>
    </div>
  );
}
