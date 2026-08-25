import { buildAttentionAssets, buildKpiSummary, buildMaintenanceHealth, daysBeforeReference } from "./executiveDashboard";

const TREND_WEEK_COUNT = 4;
const TREND_WEEK_LABELS = ["4 Weeks Ago", "3 Weeks Ago", "2 Weeks Ago", "This Week"];

function weekBucketIndex(dateString) {
  const days = daysBeforeReference(dateString);

  if (days === null || days < 0) {
    return null;
  }

  const index = TREND_WEEK_COUNT - 1 - Math.floor(days / 7);
  return index >= 0 ? index : null;
}

function formatDateOnly(value) {
  if (!value) return null;
  return String(value).slice(0, 10);
}

export function buildActivityTrend({
  workOrders = [],
  cmReports = [],
  pmOccurrences = [],
  maintenanceHistory = [],
  conditionMonitoringReadings = [],
} = {}) {
  const buckets = TREND_WEEK_LABELS.map((label) => ({
    label,
    pmCount: 0,
    cmCount: 0,
    woCount: 0,
    total: 0,
  }));

  const events = [
    ...workOrders.map((wo) => ({ type: "WO", date: wo.createdDate ?? formatDateOnly(wo.created_at) })),
    ...cmReports.map((cm) => ({ type: "CM", date: formatDateOnly(cm.created_at) })),
    ...pmOccurrences.map((pm) => ({ type: "PM", date: formatDateOnly(pm.occurrence_date) })),
    ...maintenanceHistory.map((record) => ({ type: "MH", date: formatDateOnly(record.performed_at) })),
    ...conditionMonitoringReadings.map((reading) => ({ type: "CMON", date: formatDateOnly(reading.reading_date) })),
  ];

  events.forEach((event) => {
    const index = weekBucketIndex(event.date);

    if (index === null) {
      return;
    }

    const bucket = buckets[index];
    bucket.total += 1;

    if (event.type === "PM") {
      bucket.pmCount += 1;
    } else if (event.type === "CM") {
      bucket.cmCount += 1;
    } else if (event.type === "WO") {
      bucket.woCount += 1;
    }
  });

  const lastWeek = buckets[TREND_WEEK_COUNT - 1];
  const previousWeek = buckets[TREND_WEEK_COUNT - 2];

  let correctiveMaintenanceDirection = "FLAT";
  if (lastWeek.cmCount > previousWeek.cmCount) {
    correctiveMaintenanceDirection = "UP";
  } else if (lastWeek.cmCount < previousWeek.cmCount) {
    correctiveMaintenanceDirection = "DOWN";
  }

  return { buckets, correctiveMaintenanceDirection };
}

export function buildCriticalityDistribution({ pumps = [] } = {}) {
  const counts = pumps.reduce((acc, pump) => {
    const criticality = pump.criticality ?? "UNKNOWN";
    acc[criticality] = (acc[criticality] ?? 0) + 1;
    return acc;
  }, {});

  const order = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"];

  return order
    .filter((criticality) => counts[criticality] > 0)
    .map((criticality) => ({ criticality, count: counts[criticality] }));
}

export function buildRecommendedActions(source = {}) {
  const kpis = buildKpiSummary(source);
  const health = buildMaintenanceHealth(source);
  const attentionAssets = buildAttentionAssets(source);
  const trend = buildActivityTrend(source);
  const actions = [];

  if (kpis.overduePM > 0) {
    actions.push({
      id: "overdue-pm",
      severity: "danger",
      text: `Schedule ${kpis.overduePM} overdue preventive maintenance task${kpis.overduePM === 1 ? "" : "s"}.`,
    });
  }

  if (attentionAssets.length > 0) {
    actions.push({
      id: "attention-assets",
      severity: "warning",
      text: `Review ${attentionAssets.length} high-criticality asset${attentionAssets.length === 1 ? "" : "s"} currently flagged for attention.`,
    });
  }

  if (kpis.openCorrectiveMaintenance > 0) {
    actions.push({
      id: "open-cm",
      severity: "warning",
      text: `Close out ${kpis.openCorrectiveMaintenance} open corrective maintenance report${kpis.openCorrectiveMaintenance === 1 ? "" : "s"}.`,
    });
  }

  if (trend.correctiveMaintenanceDirection === "UP") {
    actions.push({
      id: "rising-cm-trend",
      severity: "danger",
      text: "Corrective maintenance activity is rising week over week - investigate for a systemic cause.",
    });
  }

  if (health.openWorkOrders > health.closedWorkOrders) {
    actions.push({
      id: "wo-backlog",
      severity: "info",
      text: `Clear the work order backlog - ${health.openWorkOrders} open versus ${health.closedWorkOrders} closed.`,
    });
  }

  return actions;
}
