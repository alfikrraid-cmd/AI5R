import { isOpenWorkOrderStatus } from "./maintenanceHistory";

export const REFERENCE_DATE = new Date("2026-07-20T00:00:00Z");
const RECENT_ACTIVITY_WINDOW_DAYS = 14;
const OPEN_CM_STATUSES = new Set(["OPEN", "IN_PROGRESS"]);
const ATTENTION_PUMP_STATUSES = new Set(["FAULT", "MAINTENANCE"]);

export function daysBeforeReference(dateString) {
  if (!dateString) return null;
  const eventDate = new Date(`${dateString}T00:00:00Z`);
  return (REFERENCE_DATE.getTime() - eventDate.getTime()) / (1000 * 60 * 60 * 24);
}

function isRecent(dateString) {
  const days = daysBeforeReference(dateString);
  return days !== null && days >= 0 && days <= RECENT_ACTIVITY_WINDOW_DAYS;
}

export function buildKpiSummary({ pumps = [], workOrders = [], pmSchedules = [], cmReports = [], maintenanceHistory = [], pmOccurrences = [], conditionMonitoringReadings = [] } = {}) {
  const openWorkOrders = workOrders.filter((wo) => isOpenWorkOrderStatus(wo.status)).length;
  const overduePM = pmSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const upcomingPM = pmSchedules.filter((pm) => pm.status === "DUE_SOON").length;
  const openCorrectiveMaintenance = cmReports.filter((cm) => OPEN_CM_STATUSES.has(cm.status)).length;
  const openWorkOrderTags = new Set(workOrders.filter((wo) => isOpenWorkOrderStatus(wo.status)).map((wo) => wo.equipmentTag ?? wo.asset_code).filter(Boolean));
  const criticalAssets = pumps.filter((pump) => pump.criticality === "HIGH" && (ATTENTION_PUMP_STATUSES.has(pump.status) || openWorkOrderTags.has(pump.tag ?? pump.tag_number))).length;
  const recentMaintenanceActivity = [
    ...workOrders.map((wo) => wo.createdDate ?? wo.created_at),
    ...cmReports.map((cm) => cm.created_at),
    ...maintenanceHistory.map((mh) => mh.performed_at),
    ...pmOccurrences.map((pm) => pm.occurrence_date),
    ...conditionMonitoringReadings.map((reading) => reading.reading_date),
  ].filter((value) => isRecent(String(value ?? "").slice(0, 10))).length;
  const criticalFailures = cmReports.filter((cm) => cm.severity === "CRITICAL" && OPEN_CM_STATUSES.has(cm.status)).length;
  return { openWorkOrders, overduePM, upcomingPM, openCorrectiveMaintenance, criticalAssets, recentMaintenanceActivity, totalPumps: pumps.length, criticalFailures };
}

export function buildMaintenanceHealth({ pmSchedules = [], workOrders = [], cmReports = [] } = {}) {
  const totalPM = pmSchedules.length;
  const overduePM = pmSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const pmComplianceRate = totalPM === 0 ? null : Math.round(((totalPM - overduePM) / totalPM) * 100);
  const totalWorkOrders = workOrders.length;
  const closedWorkOrders = workOrders.filter((wo) => wo.status === "COMPLETED").length;
  const openWorkOrders = workOrders.filter((wo) => isOpenWorkOrderStatus(wo.status)).length;
  const cmStatusCounts = cmReports.reduce((counts, cm) => ({ ...counts, [cm.status]: (counts[cm.status] ?? 0) + 1 }), {});
  return { pmComplianceRate, totalPM, overduePM, totalWorkOrders, openWorkOrders, closedWorkOrders, cmStatusCounts };
}

export function buildEngineeringReadiness({ pumps = [] } = {}) {
  const pumpReadyCount = pumps.filter((pump) => pump.status && pump.status !== "FAULT").length;
  return { pump: pumps.length === 0 ? null : Math.round((pumpReadyCount / pumps.length) * 100), seal: null, drawing: null, document: null, knowledge: null, inventory: null };
}

export function buildEngineeringAlerts({ pmSchedules = [], cmReports = [], workOrders = [] } = {}) {
  const overduePM = pmSchedules.filter((pm) => pm.status === "OVERDUE").length;
  const criticalOpenCM = cmReports.filter((cm) => cm.severity === "CRITICAL" && OPEN_CM_STATUSES.has(cm.status)).length;
  const criticalOpenWorkOrders = workOrders.filter((wo) => wo.priority === "CRITICAL" && isOpenWorkOrderStatus(wo.status)).length;
  return { overduePM, criticalOpenCM, criticalOpenWorkOrders };
}

export function buildAttentionAssets({ pumps = [], workOrders = [], cmReports = [] } = {}) {
  const openWorkOrderCounts = workOrders.reduce((counts, wo) => {
    const tag = wo.equipmentTag ?? wo.asset_code;
    if (tag && isOpenWorkOrderStatus(wo.status)) counts[tag] = (counts[tag] ?? 0) + 1;
    return counts;
  }, {});
  const latestCMByTag = cmReports.reduce((latest, cm) => {
    const tag = cm.asset_code ?? cm.equipmentTag;
    const date = String(cm.created_at ?? "").slice(0, 10);
    if (tag && date && (!latest[tag] || latest[tag] < date)) latest[tag] = date;
    return latest;
  }, {});
  return pumps
    .map((pump) => ({ pump: pump.name ?? pump.tag ?? pump.tag_number, tag: pump.tag ?? pump.tag_number, area: pump.area ?? "N/A", status: pump.status ?? "UNKNOWN", criticality: pump.criticality ?? "N/A", openWorkOrders: openWorkOrderCounts[pump.tag ?? pump.tag_number] ?? 0, lastCorrectiveMaintenance: latestCMByTag[pump.tag ?? pump.tag_number] ?? null }))
    .filter((summary) => summary.criticality === "HIGH" && (ATTENTION_PUMP_STATUSES.has(summary.status) || summary.openWorkOrders > 0))
    .sort((a, b) => b.openWorkOrders - a.openWorkOrders);
}

export function buildUpcomingMaintenance({ pmSchedules = [] } = {}) {
  return pmSchedules.filter((pm) => pm.status === "DUE_SOON" || pm.status === "OVERDUE").sort((a, b) => String(a.nextDue ?? "9999").localeCompare(String(b.nextDue ?? "9999")));
}

export function buildRecentActivities({ workOrders = [], cmReports = [], maintenanceHistory = [], pmOccurrences = [], conditionMonitoringReadings = [] } = {}, limit = 8) {
  return [
    ...workOrders.map((wo) => ({ id: wo.id ?? wo.work_order_code, type: "WO", date: wo.createdDate ?? String(wo.created_at ?? "").slice(0, 10), title: wo.title ?? wo.description, status: wo.status, raw: wo })),
    ...cmReports.map((cm) => ({ id: cm.cm_report_code, type: "CM", date: String(cm.created_at ?? "").slice(0, 10), title: cm.failure_description, status: cm.status, raw: cm })),
    ...maintenanceHistory.map((mh) => ({ id: mh.maintenance_record_code, type: "MH", date: String(mh.performed_at ?? "").slice(0, 10), title: mh.action_taken, status: "LOGGED", raw: mh })),
    ...pmOccurrences.map((pm) => ({ id: pm.pm_occurrence_code, type: "PM", date: String(pm.occurrence_date ?? "").slice(0, 10), title: pm.pm_schedule_code ?? "PM Occurrence", status: pm.status ?? "DONE", raw: pm })),
    ...conditionMonitoringReadings.map((reading) => ({ id: reading.condition_monitoring_reading_code, type: "CMON", date: String(reading.reading_date ?? "").slice(0, 10), title: "Condition Monitoring", status: "LOGGED", raw: reading })),
  ].filter((event) => event.id).sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? ""))).slice(0, limit);
}