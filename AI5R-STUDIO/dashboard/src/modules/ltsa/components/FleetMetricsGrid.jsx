import { Card, MetricCard } from "../../../design-system";
import { formatDays, formatHours, formatPercent } from "../utils/fleetFormatters";

// MWO-LTSA-040A -- Metrics: the six required Fleet Reliability numbers,
// reusing the existing MetricCard/Card shell and the existing
// .executive-dashboard-kpi-grid layout (same responsive grid
// FleetReliabilityPanel.jsx/FleetPowerBIPanel.jsx/KpiCardGrid.jsx already
// use) -- no new grid primitive. Pump Count, Breakdown Count, and
// Critical Spare Count are already plain integers; no formatting applied.
export default function FleetMetricsGrid({
  availability,
  mtbfDays,
  mttrHours,
  pumpCount,
  breakdownCount,
  criticalSpareCount,
}) {
  const cards = [
    { title: "Availability", value: formatPercent(availability) },
    { title: "MTBF", value: formatDays(mtbfDays) },
    { title: "MTTR", value: formatHours(mttrHours) },
    { title: "Pump Count", value: pumpCount },
    { title: "Breakdown Count", value: breakdownCount },
    { title: "Critical Spare Count", value: criticalSpareCount },
  ];

  return (
    <Card title="Fleet Metrics">
      <div className="executive-dashboard-kpi-grid">
        {cards.map((card) => (
          <MetricCard key={card.title} title={card.title} value={card.value} />
        ))}
      </div>
    </Card>
  );
}
