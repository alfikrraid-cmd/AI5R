import { Card } from "../../../design-system";

// MWO-LTSA-DASHBOARD-RECOVERY-001 -- renders BasicFleetOverview
// (GET /api/ltsa/fleet/overview) exactly as returned, no derived/invented
// fields. This is the Executive Dashboard's REQUIRED core Fleet Overview
// content -- bounded (one call per canonical gateway on the backend, no
// per-pump n8n fan-out), so it is expected to load reliably even when the
// richer Reliability/Power BI panels below it cannot.
//
// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- trimmed to area/status
// distributions only: Pumps moved to FleetKpiStrip (always-visible top
// strip), Work Orders/PM/CM moved to MaintenanceActivityPanel, Seal Stock
// moved to SealInventoryPanel -- avoids showing the same bounded counts
// twice across the redesigned layout. No data dropped, only relocated;
// every field still renders somewhere on the page.
function DistributionList({ title, distribution }) {
  const entries = Object.entries(distribution ?? {});

  return (
    <div className="basic-fleet-distribution">
      <h4>{title}</h4>
      {entries.length === 0 ? (
        <p className="basic-fleet-distribution-empty">No data available.</p>
      ) : (
        <ul>
          {entries.map(([label, count]) => (
            <li key={label}>
              <span>{label}</span>
              <span>{count}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function BasicFleetOverviewPanel({ overview }) {
  return (
    <Card title="Fleet Overview">
      <div className="basic-fleet-distribution-row">
        <DistributionList title="Pumps by Area" distribution={overview.area_distribution} />
        <DistributionList title="Pumps by Status" distribution={overview.status_distribution} />
      </div>
    </Card>
  );
}
