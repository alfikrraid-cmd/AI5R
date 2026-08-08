import { useEffect, useState } from "react";
import { Card, MetricCard } from "../../../design-system";
import { getFleetReliability } from "../../../api/ai5rClient";

const UNAVAILABLE = "Unavailable";

// MWO-LTSA-037D -- Fleet Dashboard: displays the six required Fleet
// Reliability metrics, reusing the existing MetricCard shell (the same
// component KpiCardGrid.jsx already uses for every other dashboard card)
// inside the existing Card shell (the same component MaintenanceHealthPanel.jsx
// already uses). One fetch, on mount, to the already-real Fleet Reliability
// API (MWO-LTSA-037C) -- no second endpoint, no per-pump calculation
// duplicated here (FleetReliabilityService already did the aggregation).
// Null fields (no fleet data yet, e.g. no CM history anywhere) render the
// same disclosed "Unavailable" placeholder already used elsewhere in this
// dashboard (KpiCardGrid.jsx), never a fabricated number. No AI content.
function formatScore(value) {
  return value === null || value === undefined ? UNAVAILABLE : String(Math.round(value));
}

function formatDays(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${Math.round(value)} days`;
}

function formatHours(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${Math.round(value)} hrs`;
}

function formatPercent(value) {
  return value === null || value === undefined ? UNAVAILABLE : `${value}%`;
}

export default function FleetReliabilityPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getFleetReliability()
      .then((result) => {
        if (active) {
          setData(result.data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err?.message ?? "Fleet reliability API unavailable");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <Card title="Fleet Reliability">
        <p>Loading fleet reliability...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Fleet Reliability">
        <p role="alert">{error}</p>
      </Card>
    );
  }

  const cards = [
    { title: "Fleet Health", value: formatScore(data.fleet_health_score) },
    { title: "Fleet MTBF", value: formatDays(data.fleet_mtbf_days) },
    { title: "Fleet MTTR", value: formatHours(data.fleet_mttr_hours) },
    { title: "Fleet Availability", value: formatPercent(data.fleet_availability) },
    { title: "Breakdown Count", value: data.total_breakdown_count },
    { title: "Critical Spare Count", value: data.total_critical_spare_count },
  ];

  return (
    <Card title="Fleet Reliability">
      <div className="executive-dashboard-kpi-grid">
        {cards.map((card) => (
          <MetricCard key={card.title} title={card.title} value={card.value} />
        ))}
      </div>
    </Card>
  );
}
