const STATUS_VARIANT = {
  ACTIVE: "success",
  DUE_SOON: "warning",
  OVERDUE: "danger",
  ON_HOLD: "purple",
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

export function frequencyBadgeVariant(frequency) {
  return FREQUENCY_VARIANT[frequency] ?? "purple";
}

export function frequencyLabel(frequency) {
  return FREQUENCY_LABEL[frequency] ?? frequency;
}

export function triggerTypeLabel(triggerType) {
  return TRIGGER_TYPE_LABEL[triggerType] ?? triggerType;
}
