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

/**
 * Merge every PM schedule, CM report, and Work Order for a single piece of
 * equipment into one chronological (descending) timeline. Pure aggregation
 * over the existing sample data — no new data model, no persistence.
 */
export function buildAssetTimeline(equipmentTag) {
  const pmEvents = samplePMSchedules
    .filter((pm) => pm.equipmentTag === equipmentTag)
    .map((pm) => ({
      id: pm.id,
      type: "PM",
      date: pmEventDate(pm),
      title: pm.procedure,
      status: pm.status,
      assignedTechnician: pm.assignedTechnician,
      raw: pm,
    }));

  const cmEvents = sampleCMReports
    .filter((cm) => cm.equipmentTag === equipmentTag)
    .map((cm) => ({
      id: cm.id,
      type: "CM",
      date: cmEventDate(cm),
      title: cm.failureDescription,
      status: cm.status,
      assignedTechnician: cm.assignedTechnician,
      raw: cm,
    }));

  const woEvents = sampleWorkOrders
    .filter((wo) => wo.equipmentTag === equipmentTag)
    .map((wo) => ({
      id: wo.id,
      type: "WO",
      date: woEventDate(wo),
      title: wo.title,
      status: wo.status,
      assignedTechnician: wo.assignedTechnician,
      raw: wo,
    }));

  return [...pmEvents, ...cmEvents, ...woEvents].sort((a, b) => {
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

const OPEN_WORK_ORDER_STATUSES = new Set(["OPEN", "IN_PROGRESS", "ON_HOLD"]);

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
