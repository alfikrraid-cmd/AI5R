const STATUS_VARIANT = {
  OPEN: "info",
  IN_PROGRESS: "warning",
  ON_HOLD: "purple",
  COMPLETED: "success",
  CANCELLED: "danger",
};

const STATUS_LABEL = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  ON_HOLD: "On Hold",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

const PRIORITY_VARIANT = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "success",
};

export function statusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export function statusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}

export function priorityBadgeVariant(priority) {
  return PRIORITY_VARIANT[priority] ?? "purple";
}
