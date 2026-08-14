import samplePumps from "../data/samplePumps";
import samplePMSchedules from "../data/samplePMSchedules";
import sampleCMReports from "../data/sampleCMReports";
import sampleWorkOrders from "../data/sampleWorkOrders";
import { statusBadgeVariant as pmStatusBadgeVariant, statusLabel as pmStatusLabel } from "./pmStatus";
import { statusBadgeVariant as cmStatusBadgeVariant, statusLabel as cmStatusLabel } from "./cmStatus";
import {
  statusBadgeVariant as woStatusBadgeVariant,
  statusLabel as woStatusLabel,
} from "./workOrderStatus";

/**
 * This file now serves two independent consumers with two independent
 * event shapes, kept deliberately separate under distinct export names
 * rather than merged into one -- the same "disclosed overlap, not merge"
 * discipline ADR-CM-001 established, applied here to avoid a genuine
 * collision found only at implementation time (APP-ASSET360-001):
 *
 * 1. The ORIGINAL mock-data plant/asset timeline (PM/CM/WO, 3 types,
 *    "PM" meaning PM SCHEDULE) -- still used, unmodified, by
 *    ExecutiveDashboard (via utils/executiveDashboard.js),
 *    utils/analytics.js, and PumpHistoryReport.jsx. None of these three
 *    pages were in APP-ASSET360-001's scope; breaking them was not
 *    authorized, so their functions (`listAssets`, `findAssetByTag`,
 *    `buildAssetTimeline`, `buildPlantTimeline`, `buildAssetSummary`,
 *    `eventTypeBadgeVariant`, `eventTypeLabel`, `eventStatusBadgeVariant`,
 *    `eventStatusLabel`, `filterStatusLabel`) are unchanged from before
 *    this MWO.
 * 2. The NEW, real-API-backed Asset 360 event stream (WO/MH/CM/PM/CMON,
 *    5 types, "PM" meaning PM OCCURRENCE) -- used only by
 *    MaintenanceHistory.jsx (Asset 360) and its own child components
 *    (MaintenanceTimelineTable.jsx, MaintenanceEventDetailPanel.jsx).
 *    Exported under an `assetEvent*`/`buildAssetEventStream` prefix
 *    specifically to avoid colliding with (1)'s same-shaped-but-
 *    differently-meaning PM type.
 */

// ---------------------------------------------------------------------
// (1) Original mock-data plant/asset timeline -- UNCHANGED.
// ---------------------------------------------------------------------

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
  if (event.type === "PM") {
    return pmStatusBadgeVariant(event.status);
  }

  if (event.type === "CM") {
    return cmStatusBadgeVariant(event.status);
  }

  return woStatusBadgeVariant(event.status);
}

export function eventStatusLabel(event) {
  if (event.type === "PM") {
    return pmStatusLabel(event.status);
  }

  if (event.type === "CM") {
    return cmStatusLabel(event.status);
  }

  return woStatusLabel(event.status);
}

/**
 * Humanize a bare status value (as used in the Status filter dropdown,
 * where the event's type isn't available) by trying each module's label
 * map in turn. PM/CM/WO already agree on the label for every status value
 * they share (e.g. "ON_HOLD" -> "On Hold" everywhere), so this is safe
 * regardless of which type the status actually came from.
 */
export function filterStatusLabel(status) {
  const pmLabel = pmStatusLabel(status);
  if (pmLabel !== status) {
    return pmLabel;
  }

  const cmLabel = cmStatusLabel(status);
  if (cmLabel !== status) {
    return cmLabel;
  }

  return woStatusLabel(status);
}

/** Pumps available for the asset selector, sorted by tag. */
export function listAssets() {
  return [...samplePumps].sort((a, b) => a.tag.localeCompare(b.tag));
}

export function findAssetByTag(tag) {
  return samplePumps.find((pump) => pump.tag === tag) ?? null;
}

function pmEventDate(pm) {
  return pm.lastPerformed ?? pm.timeline?.[0]?.date ?? pm.nextDue ?? null;
}

function cmEventDate(cm) {
  return cm.timeline?.[0]?.date ?? null;
}

function woEventDate(wo) {
  return wo.createdDate ?? null;
}

function mapPmEvent(pm) {
  return {
    id: pm.id,
    type: "PM",
    date: pmEventDate(pm),
    title: pm.procedure,
    status: pm.status,
    assignedTechnician: pm.assignedTechnician,
    raw: pm,
  };
}

function mapCmEvent(cm) {
  return {
    id: cm.id,
    type: "CM",
    date: cmEventDate(cm),
    title: cm.failureDescription,
    status: cm.status,
    assignedTechnician: cm.assignedTechnician,
    raw: cm,
  };
}

function mapWoEvent(wo) {
  return {
    id: wo.id,
    type: "WO",
    date: woEventDate(wo),
    title: wo.title,
    status: wo.status,
    assignedTechnician: wo.assignedTechnician,
    raw: wo,
  };
}

function sortEventsDescending(events) {
  return [...events].sort((a, b) => {
    if (a.date === b.date) {
      return 0;
    }

    if (a.date === null) {
      return 1;
    }

    if (b.date === null) {
      return -1;
    }

    return a.date < b.date ? 1 : -1;
  });
}

/**
 * Merge every PM schedule, CM report, and Work Order for a single piece of
 * equipment into one chronological (descending) timeline. Pure aggregation
 * over the existing sample data — no new data model, no persistence.
 */
export function buildAssetTimeline(equipmentTag) {
  const pmEvents = samplePMSchedules.filter((pm) => pm.equipmentTag === equipmentTag).map(mapPmEvent);
  const cmEvents = sampleCMReports.filter((cm) => cm.equipmentTag === equipmentTag).map(mapCmEvent);
  const woEvents = sampleWorkOrders.filter((wo) => wo.equipmentTag === equipmentTag).map(mapWoEvent);

  return sortEventsDescending([...pmEvents, ...cmEvents, ...woEvents]);
}

/**
 * Merge every PM schedule, CM report, and Work Order across the entire
 * plant (every asset) into one chronological (descending) timeline. Same
 * event shape as `buildAssetTimeline`, just without the equipment filter —
 * used by plant-wide views such as the Executive Dashboard's Recent
 * Activities feed.
 */
export function buildPlantTimeline() {
  const pmEvents = samplePMSchedules.map(mapPmEvent);
  const cmEvents = sampleCMReports.map(mapCmEvent);
  const woEvents = sampleWorkOrders.map(mapWoEvent);

  return sortEventsDescending([...pmEvents, ...cmEvents, ...woEvents]);
}

export const OPEN_WORK_ORDER_STATUSES = new Set(["OPEN", "IN_PROGRESS", "ON_HOLD"]);

export function isOpenWorkOrderStatus(status) {
  return OPEN_WORK_ORDER_STATUSES.has(status);
}

/**
 * Derive the Asset Summary fields from a pump record and its already-built
 * timeline. All values are computed, never stored — there is no new data
 * model, only aggregation of the existing sample data.
 */
export function buildAssetSummary(pump, timeline) {
  const pmEvents = timeline.filter((event) => event.type === "PM");
  const cmEvents = timeline.filter((event) => event.type === "CM");
  const woEvents = timeline.filter((event) => event.type === "WO");

  return {
    pump: pump.name,
    tag: pump.tag,
    area: pump.area,
    status: pump.status,
    criticality: pump.criticality,
    lastPreventiveMaintenance: pmEvents[0]?.date ?? null,
    lastCorrectiveMaintenance: cmEvents[0]?.date ?? null,
    openWorkOrders: woEvents.filter((event) => OPEN_WORK_ORDER_STATUSES.has(event.status)).length,
    lastActivity: timeline[0]?.date ?? null,
  };
}

// ---------------------------------------------------------------------
// (2) New, real-API-backed Asset 360 event stream (APP-ASSET360-001, per
// ADR-ASSET360-001 / DISCOVERY-ASSET360-UI-001). MH/PM/CMON are mapped
// directly here from raw API records rather than via a dedicated
// per-domain mapping file: unlike Work Order/CM Report/PM Schedule, none
// of these three has its own workspace page yet, so this timeline is
// their only consumer today -- a dedicated mapping file per domain would
// be a premature abstraction for single-consumer logic.
// ---------------------------------------------------------------------

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
  if (event.type === "CMON") return event.status === "LEAK_DETECTED" ? "danger" : "success";
  // MH: no status column exists on maintenance_history -- "Logged" is a
  // UI-only presentation label, never a fabricated stored field.
  return "success";
}

export function assetEventStatusLabel(event) {
  if (event.type === "WO") return woStatusLabel(event.status);
  if (event.type === "CM") return cmStatusLabel(event.status);
  if (event.type === "PM") return event.status === "DONE" ? "Done" : (event.status ?? "Unknown");
  if (event.type === "CMON") return event.status === "LEAK_DETECTED" ? "Leak Detected" : "Normal";
  return "Logged";
}

export function assetFilterStatusLabel(status) {
  const woLabel = woStatusLabel(status);
  if (woLabel !== status) {
    return woLabel;
  }

  const cmLabel = cmStatusLabel(status);
  if (cmLabel !== status) {
    return cmLabel;
  }

  if (status === "LOGGED") return "Logged";
  if (status === "LEAK_DETECTED") return "Leak Detected";
  if (status === "NORMAL") return "Normal";
  if (status === "DONE") return "Done";

  return status;
}

function formatDateOnly(value) {
  if (!value) {
    return null;
  }

  return String(value).slice(0, 10);
}

/** wo is already mapped via workOrderMapping.mapWorkOrderRecord. */
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

/** record is a raw maintenance_history API record. */
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

/**
 * record is a raw cm_report API record -- read directly rather than via
 * cmMapping.mapCMReportRecord, which drops created_at (CM.jsx's own table/
 * detail never needed it). Asset 360's merged timeline needs a date for
 * every event; created_at is the same disclosed proxy
 * get_pump_last_cm() already uses server-side (cm_report has no dedicated
 * "occurred_at"/"reported_at" field).
 */
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

/** record is a raw pm_occurrence API record. */
export function mapPMOccurrenceToEvent(record) {
  const completion = Array.isArray(record.checklist_completion) ? record.checklist_completion : [];

  return {
    id: record.pm_occurrence_code,
    type: "PM",
    date: formatDateOnly(record.occurrence_date),
    title: `PM Occurrence — ${completion.length} item${completion.length === 1 ? "" : "s"} completed`,
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

/** record is a raw condition_monitoring_reading API record. */
export function mapConditionMonitoringReadingToEvent(record) {
  const leakDetected = record.mechanical_seal_leak_de === true || record.mechanical_seal_leak_nde === true;

  return {
    id: record.condition_monitoring_reading_code,
    type: "CMON",
    date: formatDateOnly(record.reading_date),
    title: leakDetected ? "Seal leak detected during inspection" : "Routine inspection — normal",
    status: leakDetected ? "LEAK_DETECTED" : "NORMAL",
    assignedTechnician: null,
    equipmentTag: record.asset_code,
    raw: {
      conditionMonitoringScheduleCode: record.condition_monitoring_schedule_code,
      mechsealTempDe: record.mechseal_temp_de,
      mechsealTempNde: record.mechseal_temp_nde,
      suctionTemp: record.suction_temp,
      dischargeTemp: record.discharge_temp,
      pumpOperatingState: record.pump_operating_state,
      leakDe: record.mechanical_seal_leak_de === true,
      leakNde: record.mechanical_seal_leak_nde === true,
    },
  };
}

/**
 * Merges all five already-fetched, already-mapped-to-event-shape source
 * arrays into one asset-scoped, descending timeline. Pure and
 * synchronous -- fetching lives in the page (MaintenanceHistory.jsx),
 * mirroring every other real-API page's fetch-in-page/compose-in-util
 * split in this codebase.
 */
export function buildAssetEventStream(sourceEvents, assetTag) {
  const matching = sourceEvents.filter((event) => event.equipmentTag === assetTag);
  return sortEventsDescending(matching);
}
