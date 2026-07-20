const STATUS_VARIANT = {
  OPEN: "info",
  IN_PROGRESS: "warning",
  ON_HOLD: "purple",
  COMPLETED: "success",
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

export function priorityBadgeVariant(priority) {
  return PRIORITY_VARIANT[priority] ?? "purple";
}
