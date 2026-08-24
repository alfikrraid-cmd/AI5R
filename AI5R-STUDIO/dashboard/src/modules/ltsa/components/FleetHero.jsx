import { Card } from "../../../design-system";
import { formatScore } from "../utils/fleetFormatters";

// MWO-LTSA-040A -- Hero: Fleet Health Score + Fleet Status, the two
// headline facts from the Executive Dashboard's Open Design layout.
// Presentational only -- data comes from the parent ExecutiveDashboard's
// single fetch of each Fleet API, reused via the shared fleetFormatters
// (no duplicated formatting logic).
export default function FleetHero({ healthScore, status }) {
  return (
    <Card title="Fleet Overview">
      <div className="fleet-hero">
        <div className="fleet-hero-item">
          <span className="fleet-hero-label">Fleet Health Score</span>
          <strong className="fleet-hero-value">{formatScore(healthScore)}</strong>
        </div>
        <div className="fleet-hero-item">
          <span className="fleet-hero-label">Fleet Status</span>
          <strong className="fleet-hero-value">{status ?? "UNKNOWN"}</strong>
        </div>
      </div>
    </Card>
  );
}
