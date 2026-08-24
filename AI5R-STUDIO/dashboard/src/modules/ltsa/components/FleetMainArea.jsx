import { Card, MetricCard } from "../../../design-system";

// MWO-LTSA-040A -- Main Area: Critical Assets, Top Risks, Fleet Insight.
// Top Risks / Fleet Insight reuse the exact same rendering pattern already
// established and tested in FleetPowerBIPanel.jsx (038B) -- no new
// derivation, no new empty-state copy. Critical Assets reuses MetricCard
// (a count, like every other metric) but is placed here, not in the
// Metrics grid, per the Open Design layout's own grouping.
export default function FleetMainArea({ criticalAssetCount, topRisks, insight }) {
  return (
    <Card title="Fleet Risk Overview">
      <div className="fleet-main-area">
        <MetricCard title="Critical Assets" value={criticalAssetCount} />

        <section>
          <h3>Top Risks</h3>
          {topRisks.length === 0 ? (
            <p>No risks reported.</p>
          ) : (
            <ul>
              {topRisks.map((risk) => (
                <li key={`${risk.tag_number}:${risk.rule_code}`}>
                  <span>{risk.tag_number}</span> — <span>{risk.title}</span> (priority {risk.priority}):{" "}
                  <span>{risk.action}</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3>Fleet Insight</h3>
          {insight ? (
            <div>
              <p>{insight.summary}</p>
              <p>{insight.action}</p>
              <p>{insight.reason}</p>
            </div>
          ) : (
            <p>No insight available.</p>
          )}
        </section>
      </div>
    </Card>
  );
}
