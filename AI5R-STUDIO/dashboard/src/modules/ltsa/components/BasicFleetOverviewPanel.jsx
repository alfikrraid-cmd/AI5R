import { useState } from "react";
import { Card } from "../../../design-system";

// MWO-LTSA-DASHBOARD-RECOVERY-001 -- renders BasicFleetOverview
// (GET /api/ltsa/fleet/overview) exactly as returned, no derived/invented
// fields.
//
// MWO-LTSA-RELIABILITY-COMMAND-CENTER-001 -- "Fleet by Contract Area" is
// now this card's primary, full-width content: the 4 canonical contract
// groups as prominent cards with a count + % of fleet (pump_count is the
// only denominator used -- both values already come straight from the
// API, this is display-only arithmetic, never a re-classification).
// Unclassified is shown with deliberately lower visual weight, as a
// data-quality signal, never merged into or hidden behind the 4 canonical
// groups. The raw area_distribution/status_distribution lists are NOT
// deleted -- they're preserved behind a "View Details" toggle so the
// primary view stays focused without losing access to the underlying
// data (this MWO's own "Do NOT delete raw area data/API" rule).
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

// Fixed display order for the 4 canonical LTSA contract groups, matching
// pump_contract_area.py's CONTRACT_AREA_GROUPS exactly. Frontend never
// derives or remaps these -- the backend is the sole canonical classifier;
// this list only controls render order of whatever contract_area_distribution
// the API already returned.
const CONTRACT_AREA_GROUPS = ["HOC", "HSC & S. Pakning", "HCC", "OM & UTL"];
const UNCLASSIFIED = "Unclassified";

function formatPercentOfFleet(count, pumpCount) {
  if (typeof count !== "number" || !pumpCount) {
    return "N/A";
  }
  return `${Math.round((count / pumpCount) * 100)}%`;
}

function ContractAreaCard({ label, count, pumpCount }) {
  const percentLabel = formatPercentOfFleet(count, pumpCount);
  const percentWidth = percentLabel === "N/A" ? 0 : parseInt(percentLabel, 10);

  return (
    <div className="contract-area-card">
      <span className="contract-area-card-label">{label}</span>
      <strong className="contract-area-card-value">{typeof count === "number" ? count : "N/A"}</strong>
      <div className="contract-area-card-bar" role="presentation">
        <div className="contract-area-card-bar-fill" style={{ width: `${percentWidth}%` }} />
      </div>
      <span className="contract-area-card-percent">{percentLabel} of fleet</span>
    </div>
  );
}

export default function BasicFleetOverviewPanel({ overview }) {
  const [showDetails, setShowDetails] = useState(false);
  const distribution = overview.contract_area_distribution;
  const unclassifiedCount = distribution ? distribution[UNCLASSIFIED] ?? 0 : null;

  return (
    <Card title="Fleet by Contract Area">
      {distribution ? (
        <div className="contract-area-grid">
          {CONTRACT_AREA_GROUPS.map((group) => (
            <ContractAreaCard key={group} label={group} count={distribution[group]} pumpCount={overview.pump_count} />
          ))}
        </div>
      ) : (
        <p className="basic-fleet-distribution-empty">N/A -- contract area data unavailable.</p>
      )}

      {typeof unclassifiedCount === "number" && unclassifiedCount > 0 ? (
        <div className="contract-area-unclassified-warning" role="status">
          <span>
            {unclassifiedCount} asset{unclassifiedCount === 1 ? "" : "s"} {unclassifiedCount === 1 ? "requires" : "require"} area classification
          </span>
        </div>
      ) : null}

      <button
        type="button"
        className="contract-area-details-toggle"
        onClick={() => setShowDetails((value) => !value)}
        aria-expanded={showDetails}
      >
        {showDetails ? "Hide Details" : "View Details"}
      </button>

      {showDetails ? (
        <div className="contract-area-details basic-fleet-distribution-row">
          <DistributionList title="Pumps by Raw Area/Location" distribution={overview.area_distribution} />
          <DistributionList title="Pumps by Status" distribution={overview.status_distribution} />
        </div>
      ) : null}
    </Card>
  );
}
