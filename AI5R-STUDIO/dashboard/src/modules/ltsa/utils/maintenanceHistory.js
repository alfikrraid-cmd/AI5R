import { statusBadgeVariant as pmStatusBadgeVariant, statusLabel as pmStatusLabel } from "./pmStatus";
import { statusBadgeVariant as cmStatusBadgeVariant, statusLabel as cmStatusLabel } from "./cmStatus";
import {
  statusBadgeVariant as woStatusBadgeVariant,
  statusLabel as woStatusLabel,
} from "./workOrderStatus";
import { isActiveLeak, leakBucket, leakPresentation, leakState } from "./leakSemantics";

// LTSA_CM_UI_REMEDIATION_R1C -- CMON event status per canonical bucket. Only a
// confirmed no-leak reading is NORMAL (green); unrecorded/partial are neutral.
const CMON_BUCKET_STATUS = { LEAK: "LEAK_DETECTED", NORMAL: "NORMAL", PARTIAL: "LEAK_PARTIALLY_RECORDED", UNKNOWN: "LEAK_NOT_RECORDED" };
const CMON_STATUS_BADGE = { LEAK_DETECTED: "danger", NORMAL: "success", LEAK_PARTIALLY_RECORDED: "neutral", LEAK_NOT_RECORDED: "neutral" };
const CMON_STATUS_LABEL = { LEAK_DETECTED: "Leak Detected", NORMAL: "No Leak", LEAK_PARTIALLY_RECORDED: "Leak Partially Recorded", LEAK_NOT_RECORDED: "Leak Not Recorded" };
const CMON_STATUS_TITLE = {
  LEAK_DETECTED: "Seal leak detected during inspection",
  NORMAL: "Routine inspection - no leak",
  LEAK_PARTIALLY_RECORDED: "Routine inspection - leak status partially recorded",
  LEAK_NOT_RECORDED: "Routine inspection - leak status not recorded",
};

function triState(value) {
  return value === true || value === false ? value : null;
}

const EVENT_TYPE_VARIANT = {
  PM: "info",
  CM: "warning",
  WO: "purple",
};

const EVENT_TYPE_LABEL = {
  PM: "PM",
  CM: "CM",
  WO: "Work Order",
};

export function eventTypeBadgeVariant(type) {
  return EVENT_TYPE_VARIANT[type] ?? "purple";
}

export function eventTypeLabel(type) {
  return EVENT_TYPE_LABEL[type] ?? type;
}

export function eventStatusBadgeVariant(event) {
  if (event.type === "PM") return pmStatusBadgeVariant(event.status);
  if (event.type === "CM") return cmStatusBadgeVariant(event.status);
  return woStatusBadgeVariant(event.status);
}

export function eventStatusLabel(event) {
  if (event.type === "PM") return pmStatusLabel(event.status);
  if (event.type === "CM") return cmStatusLabel(event.status);
  return woStatusLabel(event.status);
}

export function filterStatusLabel(status) {
  const pmLabel = pmStatusLabel(status);
  if (pmLabel !== status) return pmLabel;

  const cmLabel = cmStatusLabel(status);
  if (cmLabel !== status) return cmLabel;

  return woStatusLabel(status);
}

export function listAssets() {
  return [];
}

export function findAssetByTag() {
  return null;
}

function sortEventsDescending(events) {
  return [...events].sort((a, b) => {
    if (a.date === b.date) return 0;
    if (a.date === null) return 1;
    if (b.date === null) return -1;
    return a.date < b.date ? 1 : -1;
  });
}

export function buildAssetTimeline() {
  return [];
}

export function buildPlantTimeline() {
  return [];
}

export const OPEN_WORK_ORDER_STATUSES = new Set(["OPEN", "IN_PROGRESS", "ON_HOLD"]);

export function isOpenWorkOrderStatus(status) {
  return OPEN_WORK_ORDER_STATUSES.has(status);
}

export function buildAssetSummary(pump, timeline = []) {
  return {
    pump: pump?.name ?? pump?.tag ?? "N/A",
    tag: pump?.tag ?? null,
    area: pump?.area ?? "N/A",
    status: pump?.status ?? "UNKNOWN",
    criticality: pump?.criticality ?? "N/A",
    lastPreventiveMaintenance: null,
    lastCorrectiveMaintenance: null,
    openWorkOrders: 0,
    lastActivity: timeline[0]?.date ?? null,
  };
}

const ASSET_EVENT_TYPE_VARIANT = {
  WO: "purple",
  MH: "success",
  CM: "warning",
  PM: "info",
  CMON: "danger",
};

const ASSET_EVENT_TYPE_LABEL = {
  WO: "Work Order",
  MH: "Action Logged",
  CM: "CM Report",
  PM: "PM Occurrence",
  CMON: "Condition Monitoring",
};

export function assetEventTypeBadgeVariant(type) {
  return ASSET_EVENT_TYPE_VARIANT[type] ?? "purple";
}

export function assetEventTypeLabel(type) {
  return ASSET_EVENT_TYPE_LABEL[type] ?? type;
}

export function assetEventStatusBadgeVariant(event) {
  if (event.type === "WO") return woStatusBadgeVariant(event.status);
  if (event.type === "CM") return cmStatusBadgeVariant(event.status);
  if (event.type === "PM") return event.status === "DONE" ? "success" : "purple";
  if (event.type === "CMON") return CMON_STATUS_BADGE[event.status] ?? "neutral";
  return "success";
}

export function assetEventStatusLabel(event) {
  if (event.type === "WO") return woStatusLabel(event.status);
  if (event.type === "CM") return cmStatusLabel(event.status);
  if (event.type === "PM") return event.status === "DONE" ? "Done" : (event.status ?? "Unknown");
  if (event.type === "CMON") return event.raw?.leakState ? leakPresentation(event.raw.leakState).label : (CMON_STATUS_LABEL[event.status] ?? event.status);
  return "Logged";
}

export function assetFilterStatusLabel(status) {
  const woLabel = woStatusLabel(status);
  if (woLabel !== status) return woLabel;

  const cmLabel = cmStatusLabel(status);
  if (cmLabel !== status) return cmLabel;

  if (status === "LOGGED") return "Logged";
  if (CMON_STATUS_LABEL[status]) return CMON_STATUS_LABEL[status];
  if (status === "DONE") return "Done";

  return status;
}

function formatDateOnly(value) {
  if (!value) return null;
  return String(value).slice(0, 10);
}

export function mapWorkOrderToEvent(wo) {
  return {
    id: wo.id,
    type: "WO",
    date: wo.createdDate,
    title: wo.title || wo.description,
    status: wo.status,
    assignedTechnician: wo.assignedTechnician,
    equipmentTag: wo.equipmentTag,
    raw: wo,
  };
}

export function mapMaintenanceHistoryToEvent(record) {
  return {
    id: record.maintenance_record_code,
    type: "MH",
    date: formatDateOnly(record.performed_at),
    title: record.action_taken,
    status: "LOGGED",
    assignedTechnician: record.performed_by,
    equipmentTag: record.asset_code,
    raw: {
      actionTaken: record.action_taken,
      performedBy: record.performed_by,
      notes: record.notes,
      workOrderCode: record.work_order_code,
    },
  };
}

export function mapCMReportToEvent(record) {
  return {
    id: record.cm_report_code,
    type: "CM",
    date: formatDateOnly(record.created_at),
    title: record.failure_description,
    status: record.status,
    assignedTechnician: record.assigned_to,
    equipmentTag: record.asset_code,
    raw: {
      failureCategory: record.failure_category,
      severity: record.severity,
      priority: record.priority,
      rootCause: record.root_cause,
      immediateAction: record.immediate_action,
      correctiveAction: record.corrective_action,
      downtimeHours: record.downtime_hours,
      workOrderCode: record.work_order_code,
    },
  };
}

export function mapPMOccurrenceToEvent(record) {
  const completion = Array.isArray(record.checklist_completion) ? record.checklist_completion : [];

  return {
    id: record.pm_occurrence_code,
    type: "PM",
    date: formatDateOnly(record.occurrence_date),
    title: `PM Occurrence - ${completion.length} item${completion.length === 1 ? "" : "s"} completed`,
    status: record.status ?? "DONE",
    assignedTechnician: null,
    equipmentTag: record.asset_code,
    raw: {
      pmScheduleCode: record.pm_schedule_code,
      checklistCompletion: completion,
      workOrderCode: record.work_order_code,
    },
  };
}

export function mapConditionMonitoringReadingToEvent(record) {
  // LTSA_CM_UI_REMEDIATION_R1C -- raw DE/NDE stay tri-state (true/false/null);
  // status/title come from this occurrence's canonical leak state.
  const leakDe = triState(record.mechanical_seal_leak_de);
  const leakNde = triState(record.mechanical_seal_leak_nde);
  const state = leakState(leakDe, leakNde);
  const status = CMON_BUCKET_STATUS[leakBucket(state)];

  return {
    id: record.condition_monitoring_reading_code,
    type: "CMON",
    date: formatDateOnly(record.reading_date),
    title: CMON_STATUS_TITLE[status],
    status,
    assignedTechnician: null,
    equipmentTag: record.asset_code,
    raw: {
      conditionMonitoringScheduleCode: record.condition_monitoring_schedule_code,
      mechsealTempDe: record.mechseal_temp_de,
      mechsealTempNde: record.mechseal_temp_nde,
      suctionTemp: record.suction_temp,
      dischargeTemp: record.discharge_temp,
      pumpOperatingState: record.pump_operating_state,
      leakDe,
      leakNde,
      leakState: state,
      activeLeak: isActiveLeak(state),
    },
  };
}

export function buildAssetEventStream(sourceEvents, assetTag) {
  const matching = sourceEvents.filter((event) => event.equipmentTag === assetTag);
  return sortEventsDescending(matching);
}
