const STATUS_VARIANT = {
  OPEN: "danger",
  IN_PROGRESS: "warning",
  RESOLVED: "info",
  CLOSED: "success",
};

const STATUS_LABEL = {
  OPEN: "Open",
  IN_PROGRESS: "In Progress",
  RESOLVED: "Resolved",
  CLOSED: "Closed",
};

const SEVERITY_VARIANT = {
  MINOR: "success",
  MODERATE: "info",
  MAJOR: "warning",
  CRITICAL: "danger",
};

const PRIORITY_VARIANT = {
  CRITICAL: "danger",
  HIGH: "warning",
  MEDIUM: "info",
  LOW: "success",
};

const FAILURE_CATEGORY_LABEL = {
  MECHANICAL: "Mechanical",
  ELECTRICAL: "Electrical",
  SEAL_FAILURE: "Seal Failure",
  INSTRUMENTATION: "Instrumentation",
  PROCESS: "Process",
};

export function statusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export function statusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}

export function severityBadgeVariant(severity) {
  return SEVERITY_VARIANT[severity] ?? "purple";
}

export function priorityBadgeVariant(priority) {
  return PRIORITY_VARIANT[priority] ?? "purple";
}

export function failureCategoryLabel(failureCategory) {
  return FAILURE_CATEGORY_LABEL[failureCategory] ?? failureCategory;
}
