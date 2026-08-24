import { MetricCard } from "../../../design-system";

// MWO-LTSA-DASHBOARD-COMMAND-CENTER-001 -- always-visible glanceable top
// strip. Every value is read directly from BasicFleetOverview (bounded,
// required) or the optional Reliability/Power BI summary -- nothing here
// is derived beyond a status-label lookup, and every lookup that finds no
// match renders "N/A", never 0 or a guess (0 would falsely claim "zero
// confirmed", not "vocabulary unknown").
//
// Running/Standby: BasicFleetOverview.status_distribution's key
// vocabulary is not a confirmed enum (production evidence has shown
// "UNKNOWN" for real pumps) -- these look up common conventions
// (RUNNING/ACTIVE, STANDBY/IDLE) case-insensitively and disclose absence
// as N/A rather than assuming every fleet uses that exact vocabulary.
//
// Attention: sourced from the OPTIONAL summary (critical_asset_count,
// powerbi-backed) -- N/A whenever that optional fetch hasn't
// loaded/failed, never backfilled from the bounded overview (which has
// no equivalent field).
//
// Open WO: BasicFleetOverview.work_order_count as-is -- the bounded
// gateway's own list_work_orders() result, assumed (not verified against
// backend source in this MWO) to already represent the active/open
// backlog per that gateway's own convention. Disclosed here, not
// silently asserted as literally filtered by an "OPEN" status.
function lookupStatus(distribution, candidates) {
  const entries = Object.entries(distribution ?? {});
  for (const candidate of candidates) {
    const found = entries.find(([label]) => label?.toUpperCase() === candidate);
    if (found) return found[1];
  }
  return null;
}

export default function FleetKpiStrip({ overview, summary }) {
  const running = lookupStatus(overview.status_distribution, ["RUNNING", "ACTIVE"]);
  const standby = lookupStatus(overview.status_distribution, ["STANDBY", "IDLE"]);
  const attention = summary ? summary.critical_asset_count : null;

  const cards = [
    { title: "Pumps", value: overview.pump_count },
    { title: "Running", value: running ?? "N/A" },
    { title: "Standby", value: standby ?? "N/A" },
    { title: "Attention", value: attention ?? "N/A" },
    { title: "Open WO", value: overview.work_order_count },
  ];

  return (
    <div className="fleet-kpi-strip">
      {cards.map((card) => (
        <MetricCard key={card.title} title={card.title} value={card.value} />
      ))}
    </div>
  );
}
