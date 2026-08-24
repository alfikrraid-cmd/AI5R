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

// MWO-LTSA-FLEET-CONTRACT-AREA-001 -- fixed display order for the 4
// canonical LTSA contract groups plus Unclassified, matching
// pump_contract_area.py's CONTRACT_AREA_GROUPS + UNCLASSIFIED exactly.
// Frontend never derives or remaps these -- the backend is the sole
// canonical classifier; this list only controls render order/completeness
// of whatever contract_area_distribution the API already returned.
const CONTRACT_AREA_GROUPS = ["HOC", "HSC & S. Pakning", "HCC", "OM & UTL", "Unclassified"];

function ContractAreaList({ distribution }) {
  // Absent field (older API response, or a load that hasn't caught up to
  // this backend contract) must render an explicit unavailable state --
  // never silently fall back to raw area_distribution as if it were the
  // canonical grouping.
  if (distribution === null || distribution === undefined) {
    return (
      <div className="basic-fleet-distribution">
        <h4>Fleet by Contract Area</h4>
        <p className="basic-fleet-distribution-empty">N/A -- contract area data unavailable.</p>
      </div>
    );
  }

  return (
    <div className="basic-fleet-distribution">
      <h4>Fleet by Contract Area</h4>
      <ul>
        {CONTRACT_AREA_GROUPS.map((group) => (
          <li key={group}>
            <span>{group}</span>
            <span>{distribution[group] ?? "N/A"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function BasicFleetOverviewPanel({ overview }) {
  return (
    <Card title="Fleet Overview">
      <div className="basic-fleet-distribution-row">
        <ContractAreaList distribution={overview.contract_area_distribution} />
        <DistributionList title="Pumps by Raw Area/Location" distribution={overview.area_distribution} />
        <DistributionList title="Pumps by Status" distribution={overview.status_distribution} />
      </div>
    </Card>
  );
}
