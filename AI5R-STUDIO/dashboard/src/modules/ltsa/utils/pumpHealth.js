import colors from "../../../design-system/theme/colors";

const STATUS_VARIANT = {
  RUNNING: "success",
  STANDBY: "info",
  MAINTENANCE: "warning",
  FAULT: "danger",
};

const CRITICALITY_VARIANT = {
  HIGH: "danger",
  MEDIUM: "warning",
  LOW: "info",
};

export function healthScoreColor(score) {
  if (score >= 80) {
    return colors.success;
  }

  if (score >= 50) {
    return colors.warning;
  }

  return colors.danger;
}

export function statusBadgeVariant(status) {
  return STATUS_VARIANT[status] ?? "purple";
}

export function criticalityBadgeVariant(criticality) {
  return CRITICALITY_VARIANT[criticality] ?? "purple";
}
