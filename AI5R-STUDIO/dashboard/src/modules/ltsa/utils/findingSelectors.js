export function findingSeverityVariant(severity) {
  const normalized = String(severity ?? "").trim().toLowerCase();

  if (["critical", "high"].includes(normalized)) {
    return "danger";
  }

  if (["medium", "moderate"].includes(normalized)) {
    return "warning";
  }

  if (["low", "informational"].includes(normalized)) {
    return "info";
  }

  return "purple";
}

export function findingStatusVariant(status) {
  const normalized = String(status ?? "").trim().toLowerCase();

  if (["closed", "resolved", "approved"].includes(normalized)) {
    return "success";
  }

  if (["open", "monitoring", "in progress"].includes(normalized)) {
    return "warning";
  }

  return "info";
}
