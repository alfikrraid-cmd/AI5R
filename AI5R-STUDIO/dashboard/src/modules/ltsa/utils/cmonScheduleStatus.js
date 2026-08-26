// MWO-LTSA-PM-CMON-SCHEDULE-LIFECYCLE-016A -- badge variant/label for the
// Condition Monitoring schedule lifecycle, mirroring pmStatus.js's own
// statusBadgeVariant/statusLabel exactly (same owner-approved 5-state
// vocabulary: PLANNED/ACTIVE/OVERDUE/COMPLETED/CANCELLED). Deliberately
// duplicated rather than a shared cross-domain import, same reasoning as
// conditionMonitoringMapping.js's own isUnscheduledPlaceholder header note.
const STATUS_VARIANT = {
  PLANNED: "info",
  ACTIVE: "success",
  OVERDUE: "danger",
  COMPLETED: "purple",
  CANCELLED: "warning",
};

const STATUS_LABEL = {
  PLANNED: "Planned",
  ACTIVE: "Active",
  OVERDUE: "Overdue",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
};

export function cmonScheduleStatusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export function cmonScheduleStatusLabel(status) {
  return STATUS_LABEL[status] ?? status;
}
