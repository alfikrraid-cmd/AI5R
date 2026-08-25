import colors from "../../../design-system/theme/colors";
import spacing from "../../../design-system/theme/spacing";

// MWO-LTSA-ASSET360-CONSOLIDATION-001 -- Section A, "ASSET HEADER / HEALTH"
// KPI cards. Every value is derived from data this page already fetched
// (equipment/mechanicalSeal from the Knowledge API, pmOccurrences/
// conditionMonitoringReadings/workOrders from this MWO's own additions) --
// no new fetch, no fabricated default. A field with no supporting record
// renders "N/A", never 0 or a guessed value.

function latestDate(records, dateField) {
  const dates = (records ?? [])
    .map((record) => record[dateField])
    .filter(Boolean)
    .sort((a, b) => String(b).localeCompare(String(a)));
  return dates[0] ?? null;
}

function countOpenWorkOrders(workOrders) {
  return (workOrders ?? []).filter((wo) => !wo.closedAt).length;
}

function KpiCard({ label, value, sub }) {
  return (
    <div
      style={{
        flex: "1 1 160px",
        minWidth: 150,
        background: colors.panel,
        border: `1px solid ${colors.border}`,
        borderRadius: spacing.sm,
        padding: spacing.sm,
      }}
      data-testid={`kpi-${label.replace(/\s+/g, "-").toLowerCase()}`}
    >
      <div style={{ color: colors.textMuted, fontSize: 12 }}>{label}</div>
      <div style={{ color: colors.text, fontSize: 18, fontWeight: 600 }}>{value ?? "N/A"}</div>
      {sub ? <div style={{ color: colors.textMuted, fontSize: 12 }}>{sub}</div> : null}
    </div>
  );
}

export default function AssetHeaderKpis({ equipment, mechanicalSeal, pmOccurrences, conditionMonitoringReadings, workOrders }) {
  const lastPm = latestDate(pmOccurrences, "occurrenceDate");
  const lastCmon = latestDate(conditionMonitoringReadings, "readingDate");
  const openWorkOrderCount = countOpenWorkOrders(workOrders);

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.sm }} data-testid="asset-header-kpis">
      <KpiCard label="Current Status" value={equipment?.assetStatus ?? "N/A"} sub={equipment?.condition ? `Condition: ${equipment.condition}` : null} />
      <KpiCard label="Last PM" value={lastPm ?? "N/A"} />
      <KpiCard label="Last Condition Monitoring" value={lastCmon ?? "N/A"} />
      <KpiCard label="Open WO" value={String(openWorkOrderCount)} />
      <KpiCard label="Current Seal / Seal Status" value={mechanicalSeal?.code ?? "N/A"} sub={mechanicalSeal?.status ?? "Status: N/A"} />
    </div>
  );
}
