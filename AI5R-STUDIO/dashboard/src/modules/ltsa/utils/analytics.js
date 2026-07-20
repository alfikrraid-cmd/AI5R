import samplePumps from "../data/samplePumps";
import { buildPlantTimeline } from "./maintenanceHistory";
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

/**
 * Maintenance Activity Trend — the last four weeks of plant-wide PM/CM/WO
 * activity, oldest first, so a reader can see whether activity (and
 * specifically corrective/reactive work) is rising or falling. No chart:
 * a plain weekly count table, plus a simple UP/DOWN/FLAT direction
 * derived by comparing the two most recent weeks' corrective maintenance
 * counts — rising reactive work is the clearest "getting worse" signal
 * available in this dataset.
 */
export function buildActivityTrend() {
  const buckets = TREND_WEEK_LABELS.map((label) => ({
    label,
    pmCount: 0,
    cmCount: 0,
    woCount: 0,
    total: 0,
  }));

  buildPlantTimeline().forEach((event) => {
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
    } else {
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

/**
 * Asset Criticality Distribution — count of pumps per criticality level
 * actually present in the sample data (no synthetic zero-rows for
 * criticality levels that don't occur).
 */
export function buildCriticalityDistribution() {
  const counts = samplePumps.reduce((acc, pump) => {
    acc[pump.criticality] = (acc[pump.criticality] ?? 0) + 1;
    return acc;
  }, {});

  const order = ["HIGH", "MEDIUM", "LOW"];

  return order
    .filter((criticality) => counts[criticality] > 0)
    .map((criticality) => ({ criticality, count: counts[criticality] }));
}

/**
 * Recommended Actions — short, prioritized, plain-language next steps for
 * a manager, generated entirely from already-derived metrics (KPIs,
 * attention assets, activity trend). Every recommendation carries the
 * real count it was derived from; nothing here is a static message
 * unrelated to the underlying data.
 */
export function buildRecommendedActions() {
  const kpis = buildKpiSummary();
  const health = buildMaintenanceHealth();
  const attentionAssets = buildAttentionAssets();
  const trend = buildActivityTrend();
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
      text: "Corrective maintenance activity is rising week over week — investigate for a systemic cause.",
    });
  }

  if (health.openWorkOrders > health.closedWorkOrders) {
    actions.push({
      id: "wo-backlog",
      severity: "info",
      text: `Clear the work order backlog — ${health.openWorkOrders} open versus ${health.closedWorkOrders} closed.`,
    });
  }

  return actions;
}
