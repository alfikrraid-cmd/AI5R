import { Card } from "../../../design-system";
import { formatDays, formatHours, formatPercent, formatScore } from "../utils/fleetFormatters";

// MWO-LTSA-040A -- Bottom: Executive Summary. A plain recap list of the
// same already-fetched FleetExecutiveSummary fields Hero/Metrics/Main
// Area already render as cards -- deliberately rendered as a definition
// list, not another MetricCard grid, so this section reads as a scannable
// recap rather than a second, duplicated KPI section. No new calculation:
// every value is the same field, through the same shared formatter, the
// rest of the page already used.
export default function FleetExecutiveSummary({ summary }) {
  const rows = [
    { label: "Fleet Health", value: formatScore(summary.overall_health) },
    { label: "Fleet Status", value: summary.fleet_status },
    { label: "Critical Assets", value: summary.critical_asset_count },
    { label: "Availability", value: formatPercent(summary.fleet_availability) },
    { label: "MTBF", value: formatDays(summary.fleet_mtbf_days) },
    { label: "MTTR", value: formatHours(summary.fleet_mttr_hours) },
    { label: "Breakdown Count", value: summary.breakdown_count },
    { label: "Critical Spare Count", value: summary.critical_spare_count },
  ];

  return (
    <Card title="Executive Summary">
      <dl className="fleet-summary-list">
        {rows.map((row) => (
          <div className="fleet-summary-row" key={row.label}>
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
