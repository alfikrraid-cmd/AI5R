import samplePumps from "../data/samplePumps";
import samplePMSchedules from "../data/samplePMSchedules";
import sampleCMReports from "../data/sampleCMReports";
import sampleWorkOrders from "../data/sampleWorkOrders";
import { buildAssetSummary, buildAssetTimeline, buildPlantTimeline, isOpenWorkOrderStatus } from "./maintenanceHistory";

/**
 * Fixed reference "today" for this demo dataset, rather than the live
 * clock — the sample data is dated around mid-July 2026, and anchoring
 * "recent"/"upcoming" windows to that era keeps the dashboard's numbers
 * stable and meaningful regardless of when the app is actually opened.
 * No live synchronization is introduced by this constant — it is pure
 * derivation over static sample data, evaluated fresh on every render.
 */
export const REFERENCE_DATE = new Date("2026-07-20T00:00:00Z");
const RECENT_ACTIVITY_WINDOW_DAYS = 14;

const OPEN_CM_STATUSES = new Set(["OPEN", "IN_PROGRESS"]);
const ATTENTION_PUMP_STATUSES = new Set(["FAULT", "MAINTENANCE"]);

/** Exported so other modules (e.g. Analytics) anchor "today" identically. */
export function daysBeforeReference(dateString) {
  if (!dateString) {
    return null;
  }

  const eventDate = new Date(`${dateString}T00:00:00Z`);
  return (REFERENCE_DATE.getTime() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
}

function isRecent(dateString) {
  const days = daysBeforeReference(dateString);
  return days !== null && days >= 0 && days <= RECENT_ACTIVITY_WINDOW_DAYS;
}

/**
 * Executive KPI Cards — every value derived from existing sample data,
 * nothing hardcoded.
 */
export function buildKpiSummary() {
  const openWorkOrders = sampleWorkOrders.filter((wo) => isOpenWorkOrderStatus(wo.status)).length;
  const overduePM = samplePMSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const upcomingPM = samplePMSchedules.filter((pm) => pm.status === "DUE_SOON").length;
  const openCorrectiveMaintenance = sampleCMReports.filter((cm) => OPEN_CM_STATUSES.has(cm.status)).length;
  const criticalAssets = samplePumps.filter(
    (pump) =>
      pump.criticality === "HIGH" &&
      (ATTENTION_PUMP_STATUSES.has(pump.status) || hasOpenWorkOrder(pump.tag))
  ).length;
  const recentMaintenanceActivity = buildPlantTimeline().filter((event) => isRecent(event.date)).length;

  // RC-002 (Executive Dashboard React Implementation): Global KPI addition.
  // A plain count over already-loaded sample data -- no new gateway, no new
  // fetch, consistent with every other field in this function.
  const totalPumps = samplePumps.length;
  const criticalFailures = sampleCMReports.filter(
    (cm) => cm.severity === "CRITICAL" && OPEN_CM_STATUSES.has(cm.status)
  ).length;

  return {
    openWorkOrders,
    overduePM,
    upcomingPM,
    openCorrectiveMaintenance,
    criticalAssets,
    recentMaintenanceActivity,
    totalPumps,
    criticalFailures,
  };
}

function hasOpenWorkOrder(equipmentTag) {
  return sampleWorkOrders.some((wo) => wo.equipmentTag === equipmentTag && isOpenWorkOrderStatus(wo.status));
}

/**
 * Maintenance Health widgets — PM Compliance is an explicit sample
 * calculation (percentage of PM schedules not currently OVERDUE), not a
 * certified reliability metric.
 */
export function buildMaintenanceHealth() {
  const totalPM = samplePMSchedules.length;
  const overduePM = samplePMSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const pmComplianceRate = totalPM === 0 ? 0 : Math.round(((totalPM - overduePM) / totalPM) * 100);

  const totalWorkOrders = sampleWorkOrders.length;
  const closedWorkOrders = sampleWorkOrders.filter((wo) => wo.status === "COMPLETED").length;
  const openWorkOrders = totalWorkOrders - closedWorkOrders;

  const cmStatusCounts = sampleCMReports.reduce((counts, cm) => {
    counts[cm.status] = (counts[cm.status] ?? 0) + 1;
    return counts;
  }, {});

  return {
    pmComplianceRate,
    totalPM,
    overduePM,
    totalWorkOrders,
    openWorkOrders,
    closedWorkOrders,
    cmStatusCounts,
  };
}

/**
 * Engineering Readiness (RC-002) — Pump readiness is a real sample-data
 * percentage. Seal, Drawing, Document, Knowledge, and Inventory have no
 * backend yet (MWO-LTSA-036L: no real Seal Registry API exists to reuse
 * either) and are represented as `null` (rendered as a placeholder by
 * EngineeringReadinessPanel), not fabricated.
 */
export function buildEngineeringReadiness() {
  const pumpReadyCount = samplePumps.filter((pump) => pump.status !== "FAULT").length;

  return {
    pump: samplePumps.length === 0 ? null : Math.round((pumpReadyCount / samplePumps.length) * 100),
    seal: null,
    drawing: null,
    document: null,
    knowledge: null,
    inventory: null,
  };
}

/**
 * Engineering Alerts (RC-002) — compact plant-wide alert counts, distinct
 * from buildAttentionAssets() (per-asset detail list): this is the same
 * underlying sample data, aggregated to single counts instead of rows, so
 * no source data or filtering rule is duplicated, only the presentation
 * differs.
 */
export function buildEngineeringAlerts() {
  const overduePM = samplePMSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const criticalOpenCM = sampleCMReports.filter(
    (cm) => cm.severity === "CRITICAL" && OPEN_CM_STATUSES.has(cm.status)
  ).length;
  const criticalOpenWorkOrders = sampleWorkOrders.filter(
    (wo) => wo.priority === "CRITICAL" && isOpenWorkOrderStatus(wo.status)
  ).length;

  return { overduePM, criticalOpenCM, criticalOpenWorkOrders };
}

/**
 * Assets Requiring Attention — high-criticality pumps that are currently
 * in a concerning state (FAULT/MAINTENANCE) or carrying an open work
 * order. Derived entirely from `buildAssetSummary`/`buildAssetTimeline`
 * (built for the Maintenance History workspace), applied across every
 * pump rather than one.
 */
export function buildAttentionAssets() {
  return samplePumps
    .map((pump) => buildAssetSummary(pump, buildAssetTimeline(pump.tag)))
    .filter(
      (summary) =>
        summary.criticality === "HIGH" &&
        (ATTENTION_PUMP_STATUSES.has(summary.status) || summary.openWorkOrders > 0)
    )
    .sort((a, b) => b.openWorkOrders - a.openWorkOrders);
}

/**
 * Upcoming Maintenance — PM schedules that are due soon or already
 * overdue, soonest due date first.
 */
export function buildUpcomingMaintenance() {
  return samplePMSchedules
    .filter((pm) => pm.status === "DUE_SOON" || pm.status === "OVERDUE")
    .sort((a, b) => (a.nextDue < b.nextDue ? -1 : a.nextDue > b.nextDue ? 1 : 0));
}

/**
 * Recent Activities — the newest `limit` events across the whole plant.
 */
export function buildRecentActivities(limit = 8) {
  return buildPlantTimeline().slice(0, limit);
}
