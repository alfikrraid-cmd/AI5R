import { useEffect, useState } from "react";
import { Card, MetricCard } from "../../../design-system";
import { getFleetPowerBI } from "../../../api/ai5rClient";

const UNAVAILABLE = "Unavailable";

// MWO-LTSA-038B -- Power BI Dashboard foundation: displays the nine
// required items from the already-real Power BI API (MWO-LTSA-038A,
// GET /api/ltsa/fleet/powerbi), which itself already composes
// FleetExecutiveSummary (037E) and FleetInsight (037F) -- one fetch, on
// mount, no second endpoint. Reuses the exact same shell/format
// conventions FleetReliabilityPanel.jsx (MWO-LTSA-037D) already
// established: MetricCard inside Card, the same four numeric formatters,
// the same disclosed "Unavailable" placeholder for missing data (never a
// fabricated number). Fleet Status/Fleet Insight/Top Risks are new to
// this panel (037D's response has none of them) and are rendered as
// plain, unformatted pass-through content -- no calculation, no
// derivation, matching this MWO's own explicit rule.
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

export default function FleetPowerBIPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    getFleetPowerBI()
      .then((result) => {
        if (active) {
          setData(result.data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err?.message ?? "Fleet Power BI API unavailable");
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
      <Card title="Fleet Power BI">
        <p>Loading fleet power bi...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Fleet Power BI">
        <p role="alert">{error}</p>
      </Card>
    );
  }

  const cards = [
    { title: "Fleet Health", value: formatScore(data.overall_health) },
    { title: "Fleet Availability", value: formatPercent(data.fleet_availability) },
    { title: "Fleet MTBF", value: formatDays(data.fleet_mtbf_days) },
    { title: "Fleet MTTR", value: formatHours(data.fleet_mttr_hours) },
    { title: "Breakdown Count", value: data.breakdown_count },
    { title: "Critical Spare Count", value: data.critical_spare_count },
    { title: "Fleet Status", value: data.fleet_status },
  ];

  return (
    <Card title="Fleet Power BI">
      <div className="executive-dashboard-kpi-grid">
        {cards.map((card) => (
          <MetricCard key={card.title} title={card.title} value={card.value} />
        ))}
      </div>

      <section>
        <h3>Fleet Insight</h3>
        {data.insight ? (
          <div>
            <p>{data.insight.summary}</p>
            <p>{data.insight.action}</p>
            <p>{data.insight.reason}</p>
          </div>
        ) : (
          <p>No insight available.</p>
        )}
      </section>

      <section>
        <h3>Top Risks</h3>
        {data.top_risks.length === 0 ? (
          <p>No risks reported.</p>
        ) : (
          <ul>
            {data.top_risks.map((risk) => (
              <li key={`${risk.tag_number}:${risk.rule_code}`}>
                <span>{risk.tag_number}</span> — <span>{risk.title}</span> (priority {risk.priority}):{" "}
                <span>{risk.action}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </Card>
  );
}
