// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016 -- owner-approved 5-state
// lifecycle (PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED), computed by
// pmMapping.js's own computeDisplayStatus. DUE_SOON is removed (superseded,
// not renamed -- it was never part of the owner's approved vocabulary).
// ON_HOLD remains supported: a pre-existing stored value outside this
// MWO's own 5 states, never invented over, never silently dropped.
const STATUS_VARIANT = {
  PLANNED: "info",
  ACTIVE: "success",
  OVERDUE: "danger",
  COMPLETED: "purple",
  CANCELLED: "warning",
  ON_HOLD: "purple",
};

const STATUS_LABEL = {
  PLANNED: "Planned",
  ACTIVE: "Active",
  OVERDUE: "Overdue",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
  ON_HOLD: "On Hold",
};

const FREQUENCY_VARIANT = {
  DAILY: "info",
  WEEKLY: "info",
  MONTHLY: "info",
  RUNTIME_BASED: "purple",
};

const FREQUENCY_LABEL = {
  DAILY: "Daily",
  WEEKLY: "Weekly",
  MONTHLY: "Monthly",
  RUNTIME_BASED: "Runtime-based",
};

const TRIGGER_TYPE_LABEL = {
  CALENDAR: "Calendar",
  METER: "Runtime Meter",
};

export function statusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export function statusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}

export function frequencyBadgeVariant(frequency) {
  return FREQUENCY_VARIANT[frequency] ?? "purple";
}

export function frequencyLabel(frequency) {
  return FREQUENCY_LABEL[frequency] ?? frequency;
}

export function triggerTypeLabel(triggerType) {
  return TRIGGER_TYPE_LABEL[triggerType] ?? triggerType;
}
